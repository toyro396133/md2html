# md2html

A zero-dependency markdown-to-HTML converter CLI tool.

## Install

```bash
npm install -g .
# or
node md2html.js input.md -o output.html
```

## Usage

```bash
# Convert markdown to HTML
md2html input.md -o output.html

# Watch mode (auto-rebuild on changes)
md2html input.md -w

# Live preview server
md2html input.md -s

# Custom port for preview server
md2html input.md -s 8080

# All together
md2html input.md -o output.html -w -s
```

## API

```js
const { parse, render } = require('./md2html');

const md = '# Hello World';
const htmlAst = parse(md);
const html = render(htmlAst, 'My Page');
```

## Supported Syntax

- Headings (h1-h6)
- Bold, italic, inline code
- Code blocks with language tags
- Links, images
- Ordered and unordered lists
- Blockquotes
- Horizontal rules
- Tables (basic)
