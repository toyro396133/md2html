# md2html Demo

This is **bold text** and *italic text*.

## Features

- Zero dependencies (Node.js built-in modules only)
- Watch mode for auto-rebuild
- Live preview server
- Dark/light mode via `prefers-color-scheme`

## Code Example

```js
const md2html = require('./md2html');
const html = md2html.render(md2html.parse('# Hello'));
```

> This is a blockquote.

1. First item
2. Second item
3. Third item

Check the [GitHub repo](https://github.com/toyro396133/md2html) for more info.
