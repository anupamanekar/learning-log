import { defineCollection, z } from 'astro:content';

const blogsCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    project: z.string().optional(),
    date: z.union([z.string(), z.date()]),
    status: z.string().optional(),
    tags: z.array(z.string()).default([]),
    references: z.array(z.string()).default([]),
    topic: z.string().optional(),
    target_medium: z.string().optional(),
  }),
});

const vlogsCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    topic: z.string().optional(),
    date: z.union([z.string(), z.date()]),
    target_medium: z.string().optional(),
    estimated_duration: z.string().optional(),
    status: z.string().optional(),
    tags: z.array(z.string()).default([]),
  }),
});

const entriesCollection = defineCollection({
  type: 'content',
  schema: z.object({
    id: z.string().optional(),
    title: z.string(),
    project: z.string(),
    date: z.union([z.string(), z.date()]),
    category: z.string().optional(),
    tags: z.array(z.string()).default([]),
    severity_or_impact: z.string().optional(),
    showcase_potential: z.string().optional(),
    status: z.string().optional(),
    source_references: z.array(z.string()).default([]),
  }),
});

const thoughtsCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    date: z.union([z.string(), z.date()]),
    status: z.string().optional(),
    tags: z.array(z.string()).default([]),
    image: z.string().optional(),
  }),
});

export const collections = {
  blogs: blogsCollection,
  vlogs: vlogsCollection,
  entries: entriesCollection,
  thoughts: thoughtsCollection,
};
