# PPT HTML deck adapter design

## Capability positioning

`guizang-ppt-skill-main` is an HTML deck / web presentation workflow. It guides an agent to produce an editorial-style, horizontal-swipe presentation as a single HTML file.

It is not equivalent to a native PPTX generator. Its strongest fit is browser-presented report decks, such as technical bid presentations, design proposal showcases, project report pages, and similar narrative briefings.

## Input capabilities

The workflow can use:

- Topic or presentation theme.
- Outline or narrative structure.
- Context materials.
- Image assets.
- Theme color selection.
- Layout constraints.
- Existing documents, PPT files, articles, images, or screenshots as references.

## Output capabilities

Expected outputs are:

- A single `index.html` deck.
- Optional `images/` assets.
- Browser-based presentation.

The current capability should not promise native `.pptx` output. It should also not promise PDF output unless a separate print or export chain is explicitly designed later.

## Relationship to ZDoc

ZDoc's current main line focuses on construction-organization documents, DOCX generation, result bundles, and export flows.

An HTML deck capability should be treated as a sidecar adapter:

- It should not enter the main generation chain.
- It should not write job records, result bundles, `build`, or `output`.
- It should not automatically trigger export.
- It should not replace or overwrite DOCX generation.
- It should remain isolated from existing job, workspace, review, output, and export paths until explicitly designed and tested.

## License and dependency boundaries

The inspected directory includes an MIT License, so the design and implementation approach can be studied and potentially reused. If any code or assets are formally introduced, the original license and copyright notice must be preserved.

Third-party dependency boundaries need a separate review before product integration:

- Google Fonts.
- Lucide CDN.
- Motion One.
- Local `motion.min.js` fallback.
- Any generated image workflow.

ZDoc must not assume default network access. Offline behavior, vendoring policy, font strategy, and CDN fallback behavior need explicit design before runtime integration.

## Risks

- Users may assume the feature generates native PPTX when it actually produces an HTML deck.
- HTML injection and escaping must be handled before accepting user-provided rich content.
- CDN and font loading can fail in offline or restricted environments.
- Image copyright and generated-image provenance can create downstream risk.
- The visual system may not match ZDoc's existing document templates.
- The capability must not pollute the DOCX or export main chain.

## Recommended integration route

### Phase 1: docs-only design

Record the capability, non-goals, license boundary, dependency boundary, and expected adapter shape.

### Phase 2: pure HTML deck adapter helper

Add an `html_deck_adapter.py` helper with mock-only tests. The helper should define data structures and render-plan behavior only. Do not copy external assets in this phase.

### Phase 3: HTML deck manifest

Generate an HTML deck manifest without writing files, or write only to a dedicated sandbox or artifact boundary after that boundary is explicitly approved.

### Phase 4: manual frontend preview

Add a manual preview entry only after the helper and manifest contract are stable. The preview must be explicit and isolated from the document generation path.

### Phase 5: optional HTML package export

If approved, export an HTML package as a separate capability. It must not be coupled to DOCX or XLSX export.

### Phase 6: optional PPTX path

If native PPTX is required, design either an HTML-to-PPTX conversion path or an independent PPTX exporter as a separate project. Do not imply PPTX support from the HTML deck adapter alone.

## Non-goals

- Do not directly generate formal PPTX.
- Do not connect to `/actions/generate_async`.
- Do not write ZDoc result bundles.
- Do not trigger DOCX or XLSX export.
- Do not automatically call image generation.
- Do not default to online CDN loading.
- Do not copy `guizang-ppt-skill-main` code or assets into ZDoc without a separate license and dependency review.

## Next minimal safe task

Design the input and output schema for a future `html_deck_adapter.py` helper.

That task should:

- Stay as a pure helper plus mock tests.
- Avoid API changes.
- Avoid frontend changes.
- Avoid job, output, result bundle, and export writes.
- Avoid copying external assets.
