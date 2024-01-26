export function getBrowserName() {
    var userAgent = navigator.userAgent;
    var browserName = "Unknown";

    if (userAgent.includes("Firefox")) {
        browserName = "Mozilla Firefox";
    } else if (userAgent.includes("Chrome")) {
        browserName = "Google Chrome";
    } else if (userAgent.includes("Safari")) {
        browserName = "Apple Safari";
    } else if (userAgent.includes("Edge")) {
        browserName = "Microsoft Edge";
    } else if (userAgent.includes("Opera") || userAgent.includes("OPR")) {
        browserName = "Opera";
    } else if (userAgent.includes("MSIE") || userAgent.includes("Trident")) {
        browserName = "Internet Explorer";
    }

    return browserName;
}

export function getOSName() {
    var OS = 'Unknown';
    if (navigator.userAgent.indexOf('Win') != -1) OS = 'Windows';
    if (navigator.userAgent.indexOf('Mac') != -1) OS = 'MacOS';
    if (navigator.userAgent.indexOf('X11') != -1) OS = 'UNIX';
    if (navigator.userAgent.indexOf('Linux') != -1) OS = 'Linux';

    return OS;
}

