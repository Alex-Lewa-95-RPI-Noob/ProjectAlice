$(function () {

	let $console = $('#console');

	function onMessage(msg) {
		let payload = JSON.parse(msg.payloadString);

		let pattern = /!\[(Red|Green|Yellow|Orange|Blue|Grey)\]\((.*?)\)/gi;
		let text = payload['text'].replace(pattern, '<span class="log$1">$2</span>');

		pattern = /\*\*(.*?)\*\*/gi;
		text = text.replace(pattern, '<span class="logBold">$1</span>');

		pattern = /__(.*?)__/gi;
		text = text.replace(pattern, '<span class="logUnderlined">$1</span>');

		pattern = /--(.*?)--/gi;
		text = text.replace(pattern, '<span class="logDim">$1</span>');

		$console.append(
			'<span class="logLine">' + text + '</span>'
		);

		if ($('#checkedCheckbox').is(':visible')) {
			$console.scrollTop($console.prop('scrollHeight'));
		}
	}

	function onConnect() {
		let date = new Date();
		let time = ('0' + date.getHours()).slice(-2) + ':' + ('0' + date.getMinutes()).slice(-2) + ':' + ('0' + date.getSeconds()).slice(-2);
		$console.append(
			'<span class="logLine"><span class="logOrange">[' + time + ']</span> [AliceWatch] Watching on ' + MQTT_HOST + ':' + MQTT_PORT + ' (MQTT)</span>'
		);

		MQTT.subscribe('projectalice/logging/alicewatch')
	}

	$('#checkedCheckbox').on('click touchstart', function () {
		$(this).hide();
		$('#emptyCheckbox').show();
		return false;
	});

	$('#emptyCheckbox').on('click touchstart', function () {
		$(this).hide();
		$('#checkedCheckbox').show();
		return false;
	});

	$('[class^="fas fa-thermometer"]').on('click touchstart', function () {
		$('[class^="fas fa-thermometer"]').removeClass('alicewatchActiveVerbosity');
		$(this).addClass('alicewatchActiveVerbosity');
		$.ajax({
			url: '/alicewatch/verbosity/',
			data: {
				verbosity: $(this).data('verbosity')
			},
			type: 'POST'
		});
		return false;
	});

	mqttRegisterSelf(onConnect, 'onConnect');
	mqttRegisterSelf(onMessage, 'onMessage');
});
