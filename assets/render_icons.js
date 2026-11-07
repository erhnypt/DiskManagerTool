// node assets/render_icons.js <outDir>  — renders icon.svg at every needed size
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const out = process.argv[2], svg = fs.readFileSync(path.join(__dirname, 'icon.svg'), 'utf8');
  const b = await chromium.launch();
  for (const px of [32, 64, 128, 256, 512, 1024]) {
    const p = await b.newPage({viewport: {width: px, height: px}});
    await p.setContent(`<body style="margin:0;background:transparent">${svg.replace('<svg ', `<svg width="${px}" height="${px}" `)}</body>`);
    await p.screenshot({path: path.join(out, px + '.png'), omitBackground: true});
    await p.close();
  }
  await b.close();
})();
