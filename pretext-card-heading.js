/**
 * pretext-card-heading.js
 * Lightweight port of @chenglou/pretext's measurement technique (canvas-based
 * text measurement) used to pre-reserve product card title height before
 * the page paints, preventing layout shift in the collection grid when
 * fonts swap or titles wrap to a different number of lines.
 */
(function () {
  var canvas = document.createElement('canvas');
  var ctx = canvas.getContext('2d');

  function measureLines(text, font, maxWidth) {
    ctx.font = font;
    var words = text.split(' ');
    var lines = 1;
    var line = '';
    for (var i = 0; i < words.length; i++) {
      var test = line ? line + ' ' + words[i] : words[i];
      if (ctx.measureText(test).width > maxWidth && line) {
        lines++;
        line = words[i];
      } else {
        line = test;
      }
    }
    return lines;
  }

  function reserveHeight(el) {
    var text = el.textContent.trim();
    var style = getComputedStyle(el);
    var font = style.fontWeight + ' ' + style.fontSize + ' ' + style.fontFamily;
    var lineHeight = parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.2;
    var maxWidth = el.clientWidth || el.parentElement.clientWidth;

    var lines = measureLines(text, font, maxWidth);
    el.style.minHeight = (lines * lineHeight) + 'px';
  }

  function run() {
    document.querySelectorAll('.card__heading').forEach(reserveHeight);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
