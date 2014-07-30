#!/bin/bash

i18ndude rebuild-pot --pot src/collective/alias/locales/collective.alias.pot --create collective.alias src/collective/alias

i18ndude sync --pot src/collective/alias/locales/collective.alias.pot src/collective/alias/locales/*/LC_MESSAGES/collective.alias.po
