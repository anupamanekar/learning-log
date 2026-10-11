import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  redirects: {
    '/blogs': '/logs',
    '/notes': '/logs',
    '/vlogs': '/logs',
  },
  integrations: [
    tailwind({
      applyBaseStyles: true,
    }),
  ],
  markdown: {
    shikiConfig: {
      theme: 'github-dark-dimmed',
      wrap: true,
    },
  },
});
