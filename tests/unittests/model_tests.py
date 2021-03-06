"""
    :copyright: (c) 2011 Local Projects, all rights reserved
    :license: Affero GNU GPL v3, see LICENSE for more details.
"""

# -*- coding: utf-8 -*-

from collections import namedtuple
from datetime import (date, datetime)

from unittest2 import TestCase
from nose.tools import *

from mock import Mock

from giveaminute.models import Event
from giveaminute.models import Need
from giveaminute.models import Project
from giveaminute.models import User

class Test_User_display_name (TestCase):

    @istest
    def returns_full_first_and_last_name_when_user_has_nonzero_group_bitmask(self):
        user = User()
        user.first_name = u'Mjumbe'
        user.last_name = u'Poe'
        user.affiliation = None
        user.group_membership_bitmask = 7

        dname = user.display_name

        assert_equal(dname, u'Mjumbe Poe')

    @istest
    def returns_full_first_and_last_name_when_user_has_zero_group_bitmask(self):
        user = User()
        user.first_name = u'Mjumbe'
        user.last_name = u'Poe'
        user.affiliation = None
        user.group_membership_bitmask = 0

        dname = user.display_name

        assert_equal(dname, u'Mjumbe P.')

    @istest
    def can_handle_non_ascii_characters(self):
        user = User()
        user.first_name = u'Adé'
        user.last_name = 'F.'
        user.affiliation = None
        user.group_membership_bitmask = 0

        dname = user.display_name

        assert_equal(dname, u'Adé F.')


class Test_Project_needsByType (TestCase):
    def setup (self):
        self.__original_needs = Project.needs

    def teardown (self):
        Project.needs = self.__original_needs

    @istest
    def returns_an_empty_dictionary_when_no_needs (self):
        project = Project()
        project.needs = []

        nbt = project.needs_by_type

        assert_equal(nbt, {})

    @istest
    def returns_a_dict_with_the_need_types_as_keys (self):
        NeedStub = namedtuple('NeedStub', 'type')
        Project.needs = [NeedStub(type='a'),
                         NeedStub(type='a'),
                         NeedStub(type='b'),
                         NeedStub(type='c'),
                         NeedStub(type='d'),
                         NeedStub(type='b')]
        project = Project()

        nbt = project.needs_by_type

        assert_equal(sorted(nbt.keys()), ['a','b','c','d'])
        assert_equal(len(nbt['a']), 2)
        assert_equal(len(nbt['b']), 2)
        assert_equal(len(nbt['c']), 1)
        assert_equal(len(nbt['d']), 1)


class Test_Need_displayAddress (TestCase):

    @istest
    def returns_the_event_address_when_linked_to_event(self):
        need = Need()
        need.event = Event()
        need.event.address = '1234 Sesame Street'
        need.address = 'Skid row'

        daddress = need.display_address

        assert_equal(daddress, '1234 Sesame Street')

    @istest
    def returns_the_custom_address_when_not_linked_to_event(self):
        need = Need()
        need.event = None
        need.address = 'Skid row'

        daddress = need.display_address

        assert_equal(daddress, 'Skid row')


class Test_Need_displayDate (TestCase):

    @istest
    def returns_the_event_date_if_it_exists (self):
        need = Need()
        need.event = Event()
        need.event.start_datetime = datetime(2011, 8, 2, 12, 30, 00)

        # ... with no need date
        ddate = need.display_date
        assert_equal(ddate, 'August 2nd')

        # ... with a need date
        need.date = date(2011, 7, 11)
        ddate = need.display_date
        assert_equal(ddate, 'August 2nd')

    @istest
    def returns_the_need_date_if_no_event_set (self):
        need = Need()
        need.date = date(2011, 7, 11)

        ddate = need.display_date
        assert_equal(ddate, 'July 11th')

    @istest
    def returns_None_if_no_need_date_or_event_is_set (self):
        need = Need()

        ddate = need.display_date
        assert_is_none(ddate)


class Test_Event_rsvpServiceName (TestCase):

    @istest
    def returns_Facebook_for_facebook_urls(self):
        event = Event()
        urls = [r'http://www.facebook.com/event.php?eid=260448760649956',
                r'https://www.facebook.com/event.php?eid=260448760649956',
                r'https://WWW.FACEBOOK.COM/event.php?eid=260448760649956',]

        for url in urls:
            event.rsvp_url = url
            service_name = event.rsvp_service_name
            assert_equal(service_name, 'Facebook', "Expected service name 'Facebook' for url %r, received %r" % (url, service_name))

    @istest
    def returns_Meetup_for_meetup_urls(self):
        event = Event()
        urls = [r'http://www.meetup.com/phillypug/events/33895172/',
                r'https://www.meetup.com/phillypug/events/33895172/',
                r'http://WWW.MEETUP.COM/phillypug/events/33895172/',]

        for url in urls:
            event.rsvp_url = url
            service_name = event.rsvp_service_name
            assert_equal(service_name, 'Meetup', "Expected service name 'Meetup' for url %r, received %r" % (url, service_name))

    @istest
    def returns_Eventbrite_for_eventbrite_urls(self):
        event = Event()
        urls = [r'http://www.eventbrite.com/event/1695937595/efblike',
                r'http://WWW.EVENTBRITE.COM/event/1695937595/efblike',
                r'https://www.eventbrite.com/event/1695937595/efblike',]

        for url in urls:
            event.rsvp_url = url
            service_name = event.rsvp_service_name
            assert_equal(service_name, 'Eventbrite', "Expected service name 'Eventbrite' for url %r, received %r" % (url, service_name))

    @istest
    def returns_TicketLeap_for_ticketleap_urls(self):
        event = Event()
        urls = [r'http://tkt.ly/event/1695937595/efblike',
                r'riverstompmusicfestival.TICKETLEAP.com/riverstompmusicfestival/',
                r'http://tedxphilly.ticketleap.com/tedxphilly2011/t/b347fa25c2210005175bd2a87d0803f3/',]

        for url in urls:
            event.rsvp_url = url
            service_name = event.rsvp_service_name
            assert_equal(service_name, 'TicketLeap', "Expected service name 'TicketLeap' for url %r, received %r" % (url, service_name))

    @istest
    def return_None_for_urls_it_cant_handle(self):
        event = Event()
        urls = [r'http://www.google.com/event/1695937595/efblike',
                r'http://calendar.google.COM/event/1695937595/efblike',
                r'https://www.twitter.com/event/1695937595/efblike',
                r'www.fakefacebook.com/no-such-thing',
                r'fakefacebook.com/no-such-thing',]

        for url in urls:
            event.rsvp_url = url
            service_name = event.rsvp_service_name
            assert_is_none(service_name, "Expected service name None for url %r, received %r" % (url, service_name))

    @istest
    def returns_None_if_event_has_no_rsvpUrl(self):
        event = Event()
        event.rsvp_url = None

        assert_is_none(event.rsvp_service_name)
