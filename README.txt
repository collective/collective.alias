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

Alias-and-acquisition precedence rules
--------------------------------------

The alias object can "mask" an attribute or method on the target object. 
The precedence rules for how this works are as follows:

  1) Direct attributes of the alias (non-acquired) are always obtained from
     the alias, even if they exist on the target object.
     
  2) Attributes/objects of the following types that can be acquired from the
     alias, will always be returned acquired from the alias even if they are
     available as direct (non-acquired) attributes of the target object.
     
      - Permissions
     
  3) Otherwise, attributes that are available directly (non-acquired) on the
     target object are returned in preference over attributes acquirable from
     the alias.
     
  4) Finally, any other attributes will be acquired from the alias.

Aliasing of folders
--------------------

