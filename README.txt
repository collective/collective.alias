Introduction
============

This package provides a new content type `Alias`. An alias is configured with
a reference to another content item. It then acts as an alias for the given
item.

The following features apply to the alias and are distinct from the aliased
objects:

  * Workflow state
  * Permission/role map (as set by workflow)
  * Local roles
  * URL

Most other features are taken directly from the aliased object. The goal is
that most 'view' operations at least should work identically on the alias as
they do on the aliased object.

Aliasing of folders
--------------------

