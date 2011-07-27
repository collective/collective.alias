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
  * Portlets

In addition, certain aspects will mirror the original unless they are 
explicitly set on the alias, at which point it will have its own version.
These aspects include:

  * Content title
  * Display template (set via the `display` menu)
  * Portlets

Upgrade from Plone 3 to Plone 4
-------------------------------

With Plone 4, the UID index is converted to a UUIDIndex. The plone migration will
crash because of duplicated UID in the catalog.
So you need to fix your catalog before executing the plone migration,
go to portal_setup, Upgrades tab, choose collective.alias and 
execute the upgrade step 1 to 2.

Installation
------------

collective.alias uses Dexterity. See http://plone.org/products/dexterity for
more information.

To use the product in your own build, either depend on it in a setup.py file,
or add it to your buildout's `eggs` listing as normal.

In either case, you probably want to use Dexterity's Known Good Set of
packages to minimise the risk of package version conflicts. For example::

  [buildout]
  ...
  extends =
      ...
      http://good-py.appspot.com/release/dexterity/1.0a2

  ...
  
  [instance]
  eggs =
      Plone
      collective.alias
      ...

Refer to http://plone.org/products/dexterity to find the latest release of
the Dexterity KGS. collective.alias is tested with the 1.0 series of Dexterity
releases.

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

The "allow traversal" flag is set automatically based on the portal_type of
the original content object, though it can be modified from the alias edit
form.

The list of types that allow traversal is stored in the configuration registry
and can e edited from the `Configuration registry` control panel. If you want
to add a custom type to this list with GenericSetup, use a `registry.xml` file
like this::

    <registry>
    
        <record name="collective.alias.interfaces.IAliasSettings.traversalTypes">
          <value purge="false">
              <element>MyType</element>
          </value>
        </record>
    
    </registry>

Known issues:
-------------

The following known issues exist:

 * At the time of writing (Dexterity 1.0a2) it is not possible to create an
   Archetypes reference (e.g. the standard "Related items" field on an
   Archetypes content object, including Plone 3's default types) to an alias.
   This is due to an incompatibility between Dexterity and the Archetypes
   reference implementation.

To do:
------

 * It's not possible to edit an Alias. 
   Changes in Plone [1_, 2_] require a new way to generate the object tabs.
   The way this issue was addressed in Products.Collage [3_] doesn't work here,
   because `viewlet = provider.__getitem__("plone.contentviews")` returns a
   collective.alias.browser.ContentViews object, which doesn't have the
   prepareObjectTabs method.

.. _1: http://dev.plone.org/plone/changeset/33984
.. _2: http://dev.plone.org/plone/changeset/33984
.. _3: http://dev.plone.org/collective/changeset/111545/Products.Collage/trunk/Products/Collage/browser
