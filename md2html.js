#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const http = require('http');

function parse(md) {
  const lines = md.split('\n');
  let html = '', inCodeBlock = false, codeLang = '', codeBuf = [], inList = null, listBuf = [];

  function closeList() {
    if (inList && listBuf.length) {
      html += `<${inList}>\n${listBuf.join('')}</${inList}>\n`;
      listBuf = [];
    }
    inList = null;
  }

  function inline(text) {
    return text
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*(\S(?:.*?\S)?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(\S(?:.*?\S)?)\*/g, '<em>$1</em>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith('```')) {
      if (inCodeBlock) {
        html += `<pre><code class="language-${codeLang}">${escapeHtml(codeBuf.join('\n'))}</code></pre>\n`;
        codeBuf = [];
        inCodeBlock = false;
        codeLang = '';
      } else {
        closeList();
        codeLang = line.slice(3).trim();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuf.push(line);
      continue;
    }

    if (line.startsWith('#')) {
      closeList();
      const level = line.match(/^#{1,6}/)[0].length;
      html += `<h${level}>${inline(line.slice(level).trim())}</h${level}>\n`;
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      if (inList !== 'ul') { closeList(); inList = 'ul'; }
      listBuf.push(`<li>${inline(line.slice(2).trim())}</li>\n`);
    } else if (/^\d+\.\s/.test(line)) {
      if (inList !== 'ol') { closeList(); inList = 'ol'; }
      listBuf.push(`<li>${inline(line.replace(/^\d+\.\s*/, ''))}</li>\n`);
    } else if (line.startsWith('---') || line.startsWith('***')) {
      closeList();
      html += '<hr>\n';
    } else if (line.trim() === '') {
      closeList();
    } else {
      closeList();
      html += `<p>${inline(line)}</p>\n`;
    }
  }
  closeList();
  if (inCodeBlock) {
    html += `<pre><code>${escapeHtml(codeBuf.join('\n'))}</code></pre>\n`;
  }
  return html;
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function render(htmlContent, title) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escapeHtml(title)}</title>
<style>
  :root { --bg: #fff; --text: #1a1a2e; --code-bg: #f4f4f5; --border: #e4e4e7; --link: #2563eb; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0f172a; --text: #e2e8f0; --code-bg: #1e293b; --border: #334155; --link: #60a5fa; }
  }
  body { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem 1rem; background: var(--bg); color: var(--text); line-height: 1.7; }
  h1 { border-bottom: 2px solid var(--border); padding-bottom: .5rem; }
  h2, h3 { margin-top: 1.5em; }
  a { color: var(--link); }
  code { background: var(--code-bg); padding: .2em .4em; border-radius: 4px; font-size: .9em; }
  pre { background: var(--code-bg); padding: 1rem; border-radius: 8px; overflow-x: auto; }
  pre code { padding: 0; background: none; }
  hr { border: none; border-top: 2px solid var(--border); margin: 2rem 0; }
  blockquote { border-left: 4px solid var(--link); margin: 1em 0; padding: .5em 1em; background: var(--code-bg); border-radius: 0 8px 8px 0; }
  table { border-collapse: collapse; width: 100%; margin: 1em 0; }
  th, td { border: 1px solid var(--border); padding: .5em; text-align: left; }
  th { background: var(--code-bg); }
</style>
</head>
<body>${htmlContent}</body>
</html>`;
}

function serve(html, port) {
  const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(html);
  });
  server.listen(port, () => {
    process.stderr.write(`Server running at http://localhost:${port}\n`);
  });
}

function main() {
  const args = process.argv.slice(2);
  let inputFile, outputFile, watch = false, servePort = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--out' || args[i] === '-o') {
      outputFile = args[++i];
    } else if (args[i] === '--watch' || args[i] === '-w') {
      watch = true;
    } else if (args[i] === '--serve' || args[i] === '-s') {
      servePort = parseInt(args[++i]) || 3000;
    } else if (!inputFile) {
      inputFile = args[i];
    }
  }

  if (!inputFile) {
    process.stderr.write('Usage: md2html <input.md> [-o output.html] [-w] [-s [port]]\n');
    process.exit(1);
  }

  function convert() {
    try {
      const md = fs.readFileSync(inputFile, 'utf8');
      const title = path.basename(inputFile, '.md');
      const html = render(parse(md), title);
      const out = outputFile || inputFile.replace(/\.md$/, '.html');

      if (servePort) { serve(html, servePort); }
      if (!servePort || out) {
        fs.writeFileSync(out, html);
        process.stderr.write(`Wrote ${out}\n`);
      }
    } catch (err) {
      process.stderr.write(`Error: ${err.message}\n`);
      process.exit(1);
    }
  }

  convert();

  if (watch) {
    fs.watch(inputFile, (eventType) => {
      if (eventType === 'change') {
        process.stderr.write(`\nFile changed, rebuilding...\n`);
        convert();
      }
    });
  }
}

if (require.main === module) main();
module.exports = { parse, render };
