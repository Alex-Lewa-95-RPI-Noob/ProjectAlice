#!/usr/bin/python
# -*- coding: utf-8 -*-

from enum import Enum

class PartOfDay(Enum):
	EARLY_MORNING 	= 'Early morning'
	MORNING 		= 'Morning'
	AFTERNOON 		= 'Afternoon'
	EVENING 		= 'Evening'
	NIGHT 			= 'Night'
	SLEEPING 		= 'Sleeping'