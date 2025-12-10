import MarkdownIt from 'markdown-it'
import sanitizeHtml from 'sanitize-html'

export const useRender = () => {
  const md = new MarkdownIt({
    linkify: true,
    html: true,
    breaks: true,
    typographer: true,
  })

  function sanitizeHtmlContent(html: string) {
    return sanitizeHtml(html, {
      allowedTags: sanitizeHtml.defaults.allowedTags,
      allowedAttributes: {
        ...sanitizeHtml.defaults.allowedAttributes,
      },
      allowedSchemes: ['http', 'https', 'mailto'],
    })
  }

  function renderMarkdown(content: string) {
    return sanitizeHtmlContent(md.renderInline(content))
  }

  return {
    renderMarkdown,
  }
}
