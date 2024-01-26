import { getBrowserName, getOSName } from './userInfo.js';

console.log('Hello, World!');

var browserName = getBrowserName();
var osName = getOSName();

window.onload = function() {
    document.getElementById('greeting').innerText = `Greetings, ${getOSName()} explorer! Surfing the web with ${getBrowserName()}, I see.`;
}
