#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    openslides.agenda.models
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Models for the agenda app.

    :copyright: 2011 by the OpenSlides team, see AUTHORS.
    :license: GNU GPL, see LICENSE for more details.
"""

try:
    import json
except ImportError:
    import simplejson as json

from django.db import models

from mptt.models import MPTTModel, TreeForeignKey

from config.models import config

from projector.projector import SlideMixin
from projector.api import register_slidemodel

from agenda.api import is_summary
from utils.translation_ext import ugettext as _


class Item(MPTTModel, SlideMixin):
    """
    An Agenda Item

    MPTT-model. See http://django-mptt.github.com/django-mptt/
    """
    prefix = 'item'

    title = models.CharField(max_length=100, verbose_name=_("Title"))
    text = models.TextField(null=True, blank=True, verbose_name=_("Text"))
    transcript = models.TextField(null=True, blank=True, verbose_name=_("Transcript"))
    closed = models.BooleanField(default=False, verbose_name=_("Closed"))
    weight = models.IntegerField(default=0, verbose_name=_("Weight"))
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children')


    def slide(self):
        """
        Return a map with all Data for the Slide
        """
        data = {
            'item': self,
            'title': self.title,
            'template': 'projector/AgendaText.html',
        }

        if is_summary():
            data['items'] = self.children.all()
            data['template'] = 'projector/AgendaSummary.html'
        return data

    def set_active(self, summary=False):
        """
        Appoint this item as the active one.
        """
        super(Item, self).set_active()
        if summary:
            config["agenda_summary"] = True
        else:
            config["agenda_summary"] = False

    def set_closed(self, closed=True):
        """
        Changes the closed-status of the item.
        """
        self.closed = closed
        self.save()

    @property
    def active_parent(self):
        """
        Return True if the item has a active parent
        """
        sid = get_active_slide(only_sid=True).split()
        if  len(sid) == 2 and sid[0] == self.prefix:
            if self.get_ancestors().filter(pk=sid[0]).exists():
                return True
        return False

    @property
    def weight_form(self):
        """
        Return the WeightForm for this item.
        """
        from agenda.forms import ItemOrderForm
        try:
            parent = self.parent.id
        except AttributeError:
            parent = 0
        initial = {
            'weight': self.weight,
            'self': self.id,
            'parent': parent,
        }
        return ItemOrderForm(initial=initial, prefix="i%d" % self.id)

    @models.permalink
    def get_absolute_url(self, link='view'):
        """
        Return the URL to this item. By default it is the Link to its
        slide

        link can be:
        * view
        * delete
        """
        if link == 'view':
            return ('item_view', [str(self.id)])
        if link == 'delete':
            return ('item_delete', [str(self.id)])

    def __unicode__(self):
        return self.title

    class Meta:
        permissions = (
            ('can_see_agenda', _("Can see agenda", fixstr=True)),
            ('can_manage_agenda', _("Can manage agenda", fixstr=True)),
        )

    class MPTTMeta:
        order_insertion_by = ['weight', 'title']


register_slidemodel(Item, model_name=_('Agenda Item'))

# TODO: put this in another file

from projector.api import register_slidefunc
from agenda.slides import agenda_show

register_slidefunc(_('Agenda'), agenda_show)


from django.dispatch import receiver
from openslides.config.signals import default_config_value


@receiver(default_config_value, dispatch_uid="agenda_default_config")
def default_config(sender, key, **kwargs):
    return {
        'agenda_countdown_time': 60,
    }.get(key)

