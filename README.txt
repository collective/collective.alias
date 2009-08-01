Introduction
============

This package provides a new content type for Plone called `Alias`. An alias is
configured with a reference to another content item. It then acts as an alias
for the given item.

The alias mirrors most aspects of the original content item. If the original
is changed, the alias will be automatically updated. Certain aspects are
particular to the alias, however, including:

  * URL/path
  * portal_catalog entry
  * Workflow state
  * Permission/role map (e.g. as set by workflow)
  * Local roles
  * Content rules

In addition, certain aspects will mirror the original unless they are 
explicitly set on the alias, at which point it will have its own version.
These aspects include:

  * Content title
  * Display template (set via the `display` menu)
  * Portlets

Pasting aliases
---------------

If the user has the `collective.alias: Add Alias` permission in a given 
folder, a `Paste as alias` action will appear in the `actions` menu if there
is one or more content items on the clipboard.

Alias folder behaviour
----------------------

By default, an alias will act as a container if the original content item 
does. The alias will have the same metadata and settings as the original item,
but not its children. Children can be added to the alias directly, however.
Children can be other aliases, or regular content items.

An alias may be configured to "allow traversal". In this case, children of the
original content item will be available as children of the alias for traversal
or object access. They will *not* normally show up in folder listings, nor
will they be indexed in the `portal_catalog` as separate items. This mode is
useful for Collections and other types of content where child objects are
integral to the object.
