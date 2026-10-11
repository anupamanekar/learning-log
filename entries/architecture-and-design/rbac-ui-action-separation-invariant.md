---
id: "rbac-ui-action-separation-invariant"
title: "The UI Action Separation Pitfall: Why Tutors Could Edit Lessons but Students Couldn't View Them"
project: "adaptive-edtech-platform"
date: "2026-02-08"
category: "architecture-and-design"
tags: ["rbac", "react", "ux", "authorization", "frontend-architecture"]
severity_or_impact: "High"
showcase_potential: "Snippet"
status: "Synthesized"
source_references:
  - "documentation/BUGFIX_LESSON_VIEW_BUTTON.md"
  - "frontend/src/pages/CourseDetailPage.tsx"
---

# The UI Action Separation Pitfall: Why Tutors Could Edit Lessons but Students Couldn't View Them

## 🔍 Context & Scenario
In the **adaptive-edtech-platform** platform, course modules contain lists of lessons (videos, quizzes, markdown guides). Two primary roles interact with courses:
- **Tutors**: Author, publish, edit, and delete lesson modules.
- **Students**: Enroll in courses and consume lesson content.

## 💥 The Incident
After introducing module creation tools, students reported that clicking on a lesson did nothing, and there was no way to open or watch lessons.

When inspecting the UI code, the module list action block looked like this:
```tsx
<div className="lesson-item-actions">
  {canEdit && (
    <>
      <Link to={`/courses/lessons/${lesson.id}/edit`}>
        <Button size="small">Edit</Button>
      </Link>
      <Button size="small" variant="danger" onClick={() => handleDeleteLesson(lesson.id)}>
        Delete
      </Button>
    </>
  )}
</div>
```

Because `canEdit` was only true for course authors, **no action buttons rendered at all for students**! The entire action container was guarded behind the mutation permission, completely forgetting the read/consume action.

## 🛠️ Root Cause Analysis
- **Conflation of Management & Consumption**: The developer or agent designed the component from an authoring perspective, treating action buttons as administrative tools only.
- **Missing Student Persona Test**: E2E test suites tested course creation and tutor workflows thoroughly, but lacked a basic student assertion: `"As an enrolled student, can I click through to lesson content?"`

## 💡 The Architectural Fix & Invariant
Always decouple the primary action (universal read/consume) from role-gated administrative mutations:

```tsx
<div className="lesson-item-actions flex items-center gap-2">
  {/* Universal Primary Consumption Action */}
  <Link to={`/lessons/${lesson.id}`}>
    <Button size="small" variant="primary">View</Button>
  </Link>

  {/* Administrative Mutation Guard */}
  {canEdit && (
    <div className="flex items-center gap-1 border-l pl-2 ml-2">
      <Link to={`/courses/lessons/${lesson.id}/edit`}>
        <Button size="small" variant="secondary">Edit</Button>
      </Link>
      <Button size="small" variant="danger" onClick={() => handleDeleteLesson(lesson.id)}>
        Delete
      </Button>
    </div>
  )}
</div>
```

## 🎬 Showcase Angle
- **Key Lesson**: Always enforce a clear architectural separation between *Entity Consumption Actions* and *Entity Mutation Actions* in UI component design.
