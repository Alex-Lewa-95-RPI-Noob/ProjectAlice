# -*- coding: utf-8 -*-
import os

from core.commons import commons

__author__ = "JRK"
__version__ = "1.0.0"

import json
import time

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from core.snips.samkilla.Assistant import Assistant
from core.snips.samkilla.Entity import Entity
from core.snips.samkilla.Intent import Intent
from core.snips.samkilla.Skill import Skill
from core.snips.samkilla.exceptions.AssistantNotFoundError import AssistantNotFoundError
from core.snips.samkilla.exceptions.HttpError import HttpError
from core.snips.samkilla.models.EnumSkillImageUrl import EnumSkillImageUrl as EnumSkillImageUrlClass
from core.snips.samkilla.processors.MainProcessor import MainProcessor

EnumSkillImageUrl = EnumSkillImageUrlClass()

import core.base.Managers as managers
from core.base.Manager import Manager

class SamkillaManager(Manager):

	NAME = 'SamkillaManager'
	ROOT_URL = "https://console.snips.ai"

	def __init__(self, mainClass, devMode = True):
		super().__init__(mainClass, self.NAME)
		managers.SamkillaManager = self

		self._currentUrl = ""
		self._browser = None
		self._devMode = devMode
		self._cookie = ""
		self._userId = ""
		self._userEmail = managers.ConfigManager.getAliceConfigByName('snipsConsoleLogin')
		self._userPassword = managers.ConfigManager.getAliceConfigByName('snipsConsolePassword')
		self.Assistant = None
		self.Skill = None
		self.Intent = None
		self.Entity = None

		self._dtSlotTypesModulesValues 		= dict()
		self._dtIntentsModulesValues		= dict()
		self._dtIntentNameSkillMatching   	= dict()

		self.MainProcessor = MainProcessor(self)
		self.initActions()
		self._loadDialogTemplateMapsInConfigManager()


	def _loadDialogTemplateMapsInConfigManager(self):
		self._dtSlotTypesModulesValues, self._dtIntentsModulesValues, self._dtIntentNameSkillMatching = self.getDialogTemplatesMaps(
			runOnAssistantId=managers.LanguageManager.activeSnipsProjectId,
			languageFilter=managers.LanguageManager.activeLanguage
		)


	@property
	def userEmail(self) -> str:
		return self._userEmail

	def sync(self, moduleFilter=None, download: bool = True):
		self.log('[{}] Sync for module \'{}\''.format(self.NAME, moduleFilter if moduleFilter else "*"))

		started = self.start()

		if not started:
			self.log('[{}] No credentials. Unable to synchronize assistant with remote console'.format(self.NAME))
			return

		activeLang: str = managers.LanguageManager.activeLanguage
		activeProjectId: str = managers.LanguageManager.activeSnipsProjectId
		changes: bool = False

		try:
			changes = self.syncLocalToRemote(
				baseAssistantId=activeProjectId,
				baseLanguageFilter=activeLang,
				baseModuleFilter=moduleFilter,
				newAssistantTitle="ProjectAlice_{}".format(managers.LanguageManager.activeLanguage)
			)

			if changes:
				if download:
					self.log('[{}] Changes detected during sync, let\'s update the assistant...'.format(self.NAME))
					managers.SnipsConsoleManager.doDownload()
				else:
					self.log('[{}] Changes detected during sync but not downloading yet'.format(self.NAME))
			else:
				self.log('[{}] No changes detected during sync'.format(self.NAME))

			self.stop()
		except AssistantNotFoundError:
			self.log('[{}] Assistant project id \'{}\' for lang \'{}\' doesn\'t exist. Check your config.py'.format(self.NAME, activeProjectId, activeLang))

		return changes


	def onStart(self):
		super(SamkillaManager, self).onStart()

		if os.path.exists(os.path.join(commons.rootDir(), 'var', 'assistants', managers.LanguageManager.activeLanguage)):
			count = len([name for name in os.listdir(os.path.join(commons.rootDir(), 'var', 'assistants', managers.LanguageManager.activeLanguage)) if os.path.isdir(os.path.join(commons.rootDir(), 'var', 'assistants', managers.LanguageManager.activeLanguage, name))])
			if count <= 0:
				self.sync()
		else:
			self.sync()


	def log(self, msg):
		if self._devMode:
			self._logger.info(msg)


	def start(self):
		if managers.SnipsConsoleManager.loginCredentialsAreConfigured():
			self.initBrowser()
			self.login(self.ROOT_URL + '/home/apps')
			return True

		return False


	def stop(self):
		self._browser.quit()


	def initActions(self):
		self.Assistant = Assistant(self)
		self.Skill = Skill(self)
		self.Intent = Intent(self)
		self.Entity = Entity(self)


	def initBrowser(self):
		options = Options()
		options.headless = True
		options.add_argument('--no-sandbox')
		options.add_argument('--disable-dev-shm-usage')
		# self._browser = webdriver.Firefox('geckodriver', options=options)
		self._browser = webdriver.Chrome('chromedriver', options=options)

	def getBrowser(self):
		return self._browser

	def reloadBrowserPage(self):
		self._browser.execute_script("location.reload()")

	def visitUrl(self, url):
		self._currentUrl = url
		self._browser.get(url)
		time.sleep(0.1)
		# self.log("[Browser] " + self._browser.title +' - ' + self._browser.current_url)

	def login(self, url):
		self.visitUrl(url)
		self._browser.find_element_by_class_name('cookies-analytics-info__ok-button').click()
		self._browser.find_element_by_name('email').send_keys(self._userEmail)
		self._browser.find_element_by_name('password').send_keys(self._userPassword)
		self._browser.find_element_by_css_selector('.login-page__section-public__form .button[type=submit]').click()
		self._cookie = self._browser.execute_script("return document.cookie")
		self._userId =  self._browser.execute_script("return window._loggedInUser['id']")

	# @TODO batch gql requests
	def postGQLBrowserly(self, payload, jsonRequest=True, dataReadyResponse=True, rawResponse=False):
		if jsonRequest:
			payload = json.dumps(payload)

		payload = payload.replace("'", "__SINGLE_QUOTES__").replace("\\n", " ")

		# self.log(payload)
		# self._browser.execute_script('console.log(\'' + payload + '\')')
		# self._browser.execute_script('console.log(\'' + payload + '\'.replace(/__SINGLE_QUOTES__/g,"\'").replace(/__QUOTES__/g,\'\\\\"\'))')

		self._browser.execute_script("document.title = 'loading'")
		self._browser.execute_script('fetch("/gql", {method: "POST", headers:{"accept":"*/*","content-type":"application/json"}, credentials: "same-origin", body:\'' + payload + '\'.replace(/__SINGLE_QUOTES__/g,"\'").replace(/__QUOTES__/g,\'\\\\"\')}).then((data) => { data.text().then((text) => { document.title = text; }); })')
		wait = WebDriverWait(self._browser, 10)
		wait.until(EC.title_contains('{'))
		response = self._browser.execute_script("return document.title")
		self._browser.execute_script("document.title = 'idle'")
		# self.log(response)

		jsonResponse = json.loads(response)

		if 'errors' in jsonResponse[0]:
			firstError = jsonResponse[0]['errors'][0]
			complexMessage = firstError['message']
			path = firstError['path'] if 'path' in firstError else ['']

			try:
				errorDetails = json.loads(complexMessage)
			except:
				errorDetails = {'status': 0}

			errorResponse = {
				"code": errorDetails['status'],
				"message": complexMessage,
				"context": path
			}

			raise HttpError(errorResponse['code'], errorResponse['message'], errorResponse['context'])

		if rawResponse:
			return response

		if not dataReadyResponse:
			return jsonResponse

		return jsonResponse[0]['data']

	# Do not use for authenticated function like MUTATIONS (and maybe certain QUERY)
	# console-session is randomly present from browser (document.cookie) so we can't authenticated him automatically
	def postGQLNatively(self, payload):
		# console-session cookie must be present
		url = self.ROOT_URL + '/gql'
		headers = {
			'Pragma': 'no-cache',
			'Origin': self.ROOT_URL,
			'Accept-Encoding': 'gzip, deflate, br',
			'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36',
			'content-type': 'application/json',
			'accept': '*/*',
			'Cache-Control': 'no-cache',
			'Referer': self.ROOT_URL + '/home/assistants',
			'Cookie': self._cookie,
			'Connection': 'keep-alive'
		}
		return requests.post(url=url, data=payload, headers=headers)


	def findRunnableAssistant(self, assistantId, assistantLanguage, newAssistantTitle="AliceProject", persistLocal=False):
		runOnAssistantId = None

		if assistantId == '':
			assistantId = None

		# AssistantId provided
		if assistantId:
			if not self.Assistant.exists(assistantId):
				# If not found remotely, stop everything
				raise AssistantNotFoundError(4001, "Assistant with id {} not found".format(assistantId), ["assistant"])
			else:
				# If found remotely, just use it
				runOnAssistantId = assistantId
				self.log("Using provided assistantId: {}".format(runOnAssistantId))


		if not runOnAssistantId:
			# Try to find the first local assistant for the targeted language
			localFirstAssistantId = self.MainProcessor.getLocalFirstAssistantByLanguage(assistantLanguage=assistantLanguage, returnId=True)

			if localFirstAssistantId is None or not self.Assistant.exists(localFirstAssistantId):
				# If not found remotely, create a new one
				runOnAssistantId = self.Assistant.create(title=newAssistantTitle, language=assistantLanguage)
				self.log("Using new assistantId: {}".format(runOnAssistantId))
			else:
				# If found remotely, just use it
				runOnAssistantId = localFirstAssistantId
				self.log("Using first local assistantId: {}".format(runOnAssistantId))

		# Add assistant in cache locally if it isn't the case
		self.MainProcessor.syncRemoteToLocalAssistant(
			assistantId=runOnAssistantId,
			assistantLanguage=assistantLanguage,
			assistantTitle=self.Assistant.getTitleById(runOnAssistantId)
		)

		return runOnAssistantId

	def syncLocalToRemote(self, baseAssistantId, baseModuleFilter, newAssistantTitle="AliceProject", baseLanguageFilter="en"):
		# RemoteFetch/LocalCheck/CreateIfNeeded: assistant
		runOnAssistantId = self.findRunnableAssistant(
			assistantId=baseAssistantId,
			assistantLanguage=baseLanguageFilter,
			newAssistantTitle=newAssistantTitle,
			persistLocal=True
		)

		if managers.LanguageManager.activeSnipsProjectId != runOnAssistantId:
			managers.LanguageManager.changeActiveSnipsProjectIdForLanguage(runOnAssistantId, baseLanguageFilter)

		# From module intents files to dict then push to SnipsConsole
		changes = self.MainProcessor.syncLocalToRemote(runOnAssistantId, moduleFilter=baseModuleFilter, languageFilter=baseLanguageFilter)

		return changes


	def syncRemoteToLocal(self, baseAssistantId, baseModuleFilter, baseLanguageFilter="en"):
		# RemoteFetch/LocalCheck/CreateIfNeeded: assistant
		runOnAssistantId = self.findRunnableAssistant(
			assistantId=baseAssistantId,
			assistantLanguage=baseLanguageFilter,
			persistLocal=False
		)

		# From SnipsConsole objects to module intents files
		self.MainProcessor.syncRemoteToLocal(runOnAssistantId, languageFilter=baseLanguageFilter, moduleFilter=baseModuleFilter)


	def getDialogTemplatesMaps(self, runOnAssistantId, languageFilter, moduleFilter=None):
		return self.MainProcessor.buildMapsFromDialogTemplates(runOnAssistantId, languageFilter=languageFilter, moduleFilter=moduleFilter)


	def getIntentsByModuleName(self, runOnAssistantId, languageFilter, moduleFilter=None):
		slotTypesModulesValues, intentsModulesValues, intentNameSkillMatching = self.getDialogTemplatesMaps(
			runOnAssistantId=runOnAssistantId,
			languageFilter=languageFilter
		)

		intents = list()

		for dtIntentName, dtModuleName in intentNameSkillMatching.items():
			if dtModuleName == moduleFilter:
				intents.append({
					"name": dtIntentName,
					"description": intentsModulesValues[dtIntentName]['__otherattributes__']['description']
				})

		return intents

	def getUtterancesByIntentName(self, runOnAssistantId, languageFilter, intentFilter=None):
		slotTypesModulesValues, intentsModulesValues, intentNameSkillMatching = self.getDialogTemplatesMaps(
			runOnAssistantId=runOnAssistantId,
			languageFilter=languageFilter
		)

		utterances = list()

		for dtIntentName, dtModuleName in intentNameSkillMatching.items():
			if dtIntentName == intentFilter:
				for utterance, _ in intentsModulesValues[dtIntentName]['utterances'].items():
					utterances.append({
						"sentence": utterance
					})

		return utterances



	@property
	def dtSlotTypesModulesValues(self) -> dict:
		return self._dtSlotTypesModulesValues


	@property
	def dtIntentsModulesValues(self) -> dict:
		return self._dtIntentsModulesValues


	@property
	def dtIntentNameSkillMatching(self) -> dict:
		return self._dtIntentNameSkillMatching
