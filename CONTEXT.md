# StepShot Domain Context

## Annotation Document
The editable image together with its ordered annotations and current background. It excludes transient interaction state.

## Annotation Record
A complete, self-contained representation of one annotation in an annotation document. It identifies the annotation kind and preserves the annotation's user-visible state.

## Document History
The ordered set of prior annotation-document states used to move backward and forward through accepted editing actions.

## Accepted Mutation
A change to the annotation document that produces a new document state and may become part of document history. Rejected changes do not alter the document or its history.

## Transient Interaction State
Selection, text-editing state, previews, resize handles, and in-progress gestures. It belongs to the current editing interaction, not to the annotation document or document history.

## Immutable Record
An annotation record whose value cannot be changed after creation. An accepted mutation creates a new annotation-document state instead of changing a record held by an earlier history entry.

## Atomic Restoration
Restoration either reconstructs the complete requested annotation document or rejects the snapshot without leaving a partial document state.

## Mutation Result
The internal outcome of submitting a document change. It identifies whether the change was accepted and carries the resulting state and update information needed by the canvas adapter.

## Framework-Neutral Image Value
The annotation document's immutable background image representation. It contains image data without depending on Qt or another rendering framework; the canvas adapter converts it to and from a Qt image value.

## Complete State Equality
Equality over all observable annotation-document values: background pixels, annotation order, geometry, and user-visible properties. Transient interaction state is excluded.

## Restoration Rejection
A typed result indicating that a snapshot could not be restored because its records are unknown or malformed. It leaves the current annotation document unchanged.

## Image Value
An immutable framework-neutral image value containing pixel bytes, width, height, color format, stride, and device-pixel ratio metadata. It is converted to and from Qt image values by the canvas adapter.

## Record Version
The explicit version attached to a serialized annotation document. Unsupported versions produce a restoration rejection instead of best-effort conversion.

## Single History Owner
The document/history module's ownership of the current annotation document and both undo/redo stacks. The canvas adapter holds no duplicate history state.

## Owned Pixel Bytes
Pixel bytes copied into an image value's own storage at creation or restoration. The image value does not depend on a Qt buffer's lifetime or later mutation.

## Fixed Adapter Registry
The complete, explicitly assembled set of annotation adapters supported by the application. It is not modified dynamically at runtime.

## Fail-Closed Capture
Rejecting document-state creation when an annotation has no registered adapter, rather than silently omitting that annotation from the state or history.

## In-Memory Record Contract
A versioned record format used only for document/history state and undo/redo during a running application. It is not a persistent file format or compatibility promise.

## Staged Delivery
A sequence of separately reviewable changes, each with focused tests and full-suite verification, where later seams are not introduced until earlier document/history behavior is stable.

## Adapter Error Presentation
The canvas or application adapter's responsibility for turning a framework-neutral restoration rejection into the existing user-visible error behavior. The document/history module remains framework-neutral and does not present errors.

## Contract Coverage
Tests that represent each observable editing contract at the highest appropriate seam: document/history tests for state and history, and canvas interaction tests for Qt behavior and rendered output.

## Deletion-Test Completion
The point at which obsolete snapshot methods and duplicate history paths have no callers, are removed, and their replacement interface is covered by behavior tests.

## Internal Document Interface
The document/history interface is an internal seam for StepShot modules. It has no external plugin or third-party compatibility promise.

## Undo Granularity
The rule that each existing user-visible editing action creates exactly one history entry, while loading a screenshot creates the initial state without an undo entry.

## Reset Mutation
The single undoable document mutation that implements Reset All and restores the pre-crop original image and current reset annotation behavior.

## Settled Design
A document/history design whose alternatives have been decided, whose contracts are written down, and which is ready for implementation without silently assumed choices.

## Screenshot
A captured image together with its live annotation document and capture metadata. It preserves the original capture separately from the current edited state.

## Screenshot Inventory
The ordered in-memory set of screenshots captured during a session. It identifies the active screenshot and preserves each screenshot's annotation document and editing history.

## Active Screenshot
The screenshot in the inventory currently shown on the canvas. Editing actions apply to the active screenshot only.
