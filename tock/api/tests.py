# -*- coding: utf-8 -*-

import csv
import datetime
import json

from django.test import TestCase
from django.core.urlresolvers import reverse

from django_webtest import WebTest

from api.views import get_timecards, TimecardList, ProjectList, TimecardSerializer
from projects.factories import AccountingCodeFactory, ProjectFactory
from hours.factories import (
    UserFactory, ReportingPeriodFactory, TimecardFactory, TimecardObjectFactory,
)
from hours.models import Timecard, TimecardObject
from projects.models import Project

from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from employees.models import UserData, EmployeeGrade

from rest_framework.authtoken.models import Token

from django.test.client import Client
from rest_framework.test import APIClient

# common client for all API tests
def client(self):
    self.request_user = User.objects.get_or_create(username='aaron.snow')[0]
    self.token = Token.objects.get_or_create(user=self.request_user)[0].key
    self.client = APIClient()
    self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token)
    return self.client

# common fixtures for all API tests
FIXTURES = [
    'tock/fixtures/prod_user.json',
    'projects/fixtures/projects.json',
    'hours/fixtures/timecards.json',
    'employees/fixtures/user_data.json'
]

class AddHoursTests(WebTest):
    fixtures = FIXTURES

    def setUp(self):
        self.payload = {'username': 'aaron.snow',
                    'end_date': '2015-06-08',
                    'id': '2',
                    'hours_spent': '10'}

    def test_error_on_bad_rp(self):
        """ Test for handling of an incorrect reporting period."""
        test_payload = self.payload
        test_payload['end_date'] = '1999-12-31'
        response = client(self).post(reverse('AddHoursView'), test_payload)
        self.assertContains(response, 'ReportingPeriod', status_code=400)

    def test_error_on_bad_project(self):
        """ Test for handling of an incorrect project."""
        test_payload = self.payload
        test_payload['id'] = '12345'
        response = client(self).post(reverse('AddHoursView'), test_payload)
        self.assertContains(response, 'Project', status_code=400)

    def test_error_on_bad_user(self):
        """ Test for handling of an incorrect user."""
        test_payload = self.payload
        test_payload['username'] = 'barry.bonds'
        response = client(self).post(reverse('AddHoursView'), test_payload)
        self.assertContains(response, 'User', status_code=400)

    def test_successful_add_none_existing(self):
        """ Test that a new TimecardObject is created if there is no
        existing TimecardObject with the same project info. """
        timecard = Timecard.objects.get(
            user__username=self.payload['username'],
            reporting_period__end_date=self.payload['end_date']
            )
        tcos = TimecardObject.objects.filter(
            timecard=timecard).values_list('project', flat=True)
        self.assertFalse(self.payload['id'] in tcos)
        response = client(self).post(reverse('AddHoursView'), self.payload)
        self.assertContains(response, '10 hours', status_code=200)
        self.assertTrue(self.payload['id'] not in tcos)

    def test_successful_add_with_single_existing(self):
        """ Test that an existing single TimecardObject with project info
        matching the request project info is updated with additional hours. """
        test_payload = self.payload
        test_payload['id'] = '1'
        timecard = Timecard.objects.get(
            user__username=test_payload['username'],
            reporting_period__end_date=test_payload['end_date']
            )
        old_tcos = len(TimecardObject.objects.filter(timecard=timecard))
        response = client(self).post(reverse('AddHoursView'), test_payload)
        new_tcos = len(TimecardObject.objects.filter(timecard=timecard))
        self.assertTrue(old_tcos == new_tcos)
        self.assertContains(response, '10 hours', status_code=200)

    def test_successful_add_with_multiple_existing(self):
        """ Test that a new TimecardObject is created if there are already
        multiple TimecardObjects with the same project info as the request. """
        test_payload = self.payload
        test_payload['id'] = '1'
        project = Project.objects.get(id='1')
        timecard = Timecard.objects.get(
            user__username=test_payload['username'],
            reporting_period__end_date=test_payload['end_date']
            )
        TimecardObject.objects.create(
            timecard=timecard, project=project, hours_spent=10)
        response = client(self).post(reverse('AddHoursView'), test_payload)
        tcos = TimecardObject.objects.filter(timecard=timecard).count()
        self.assertContains(response, '10 hours', status_code=200)
        self.assertEqual(tcos, 3)

class ProjectsAPITests(TestCase):
    fixtures = FIXTURES

    def test_projects_json(self):
        pass

class ProjectInstanceAPITests(WebTest):
    fixtures = FIXTURES

    def test_projects_json(self):
        res = client(self).get(reverse('ProjectInstanceView', kwargs={'pk': '29'})).data
        self.assertEqual(res['name'], "Consulting - Agile BPA")
        self.assertEqual(res['start_date'], "2016-01-01")
        self.assertEqual(res['end_date'], None)

class UsersAPITests(TestCase):
    fixtures = FIXTURES

    def test_users_json(self):
        pass

    def test_users_csv(self):
        pass

class TimecardsAPITests(WebTest):
    fixtures = FIXTURES

    def test_timecards_json(self):
        """ Check that the timecards are rendered in json format correctly """
        res = client(self).get(reverse('TimecardList')).content
        clean_res = json.loads(res.decode())
        self.assertEqual(len(clean_res), 2)

    # TODO: test with more diverse data
    def test_get_timecards(self):
        """ Check that get time cards returns the correct queryset """
        # Check with no params
        queryset = get_timecards(TimecardList.queryset)
        self.assertEqual(len(queryset), 2)
        # Check with after param
        queryset = get_timecards(TimecardList.queryset,
            params={'after': '2020-12-31'})
        self.assertEqual(len(queryset), 0)

        # Check with date param
        queryset = get_timecards(TimecardList.queryset,
                                 params={'date': '2000-01-01'})
        self.assertEqual(len(queryset), 0)
        queryset = get_timecards(TimecardList.queryset,
                                 params={'date': '2015-06-08'})
        self.assertEqual(len(queryset), 1)
        # Check with user param
        queryset = get_timecards(TimecardList.queryset,
                                 params={'user': '1'})
        self.assertEqual(len(queryset), 2)
        queryset = get_timecards(TimecardList.queryset,
                                 params={'user': 'aaron.snow'})
        self.assertEqual(len(queryset), 2)
        queryset = get_timecards(TimecardList.queryset,
                                 params={'user': '22'})
        self.assertEqual(len(queryset), 0)
        # Check with project param
        queryset = get_timecards(TimecardList.queryset,
                                 params={'project': '1'})
        self.assertEqual(len(queryset), 2)
        queryset = get_timecards(TimecardList.queryset,
                                 params={'project': 'Out Of Office'})
        self.assertEqual(len(queryset), 2)
        queryset = get_timecards(TimecardList.queryset,
                                 params={'project': '22'})
        self.assertEqual(len(queryset), 0)

    def test_get_unsubmitted_timecards(self):
        """ Check that get time cards returns the correct queryset """
        queryset = get_timecards(
            TimecardList.queryset,
            params={'submitted': 'no'}
        )
        self.assertEqual(len(queryset), 1)

        queryset = get_timecards(
            TimecardList.queryset,
            params={'submitted': 'yes'}
        )
        self.assertEqual(len(queryset), 2)

        queryset = get_timecards(
            TimecardList.queryset,
            params={'submitted': 'foo'}
        )
        self.assertEqual(len(queryset), 2)

class TestAggregates(WebTest):

    def setUp(self):
        super(TestAggregates, self).setUp()
        self.user = UserFactory()
        self.userdata = UserData.objects.create(user=self.user)
        self.billable_code = AccountingCodeFactory(billable=True)
        self.nonbillable_code = AccountingCodeFactory(billable=False)
        self.billable_project = ProjectFactory(accounting_code=self.billable_code)
        self.nonbillable_project = ProjectFactory(accounting_code=self.nonbillable_code)
        self.period = ReportingPeriodFactory(start_date=datetime.datetime(2015, 11, 1))
        self.timecard = TimecardFactory(user=self.user, reporting_period=self.period)
        self.grade = EmployeeGrade.objects.create(employee=self.user, grade=15, g_start_date=datetime.datetime(2016, 1, 1))
        self.timecard_objects = [
            TimecardObjectFactory(
                timecard=self.timecard,
                project=self.billable_project,
                hours_spent=15,
                grade=self.grade,
            ),
            TimecardObjectFactory(
                timecard=self.timecard,
                project=self.nonbillable_project,
                hours_spent=5,
                grade=self.grade
            ),
        ]

    def test_hours_by_quarter(self):
        response = client(self).get(reverse('HoursByQuarter')).data
        self.assertEqual(len(response), 1)
        row = response[0]
        self.assertEqual(row['billable'], 15)
        self.assertEqual(row['nonbillable'], 5)
        self.assertEqual(row['total'], 20)
        self.assertEqual(row['year'], 2016)
        self.assertEqual(row['quarter'], 1)

    def test_hours_by_quarter_with_unsubmitted_timecards(self):
        """ Check that unsubmitted timecards are not counted  """
        timecard_unsubmit = TimecardFactory(
            user=self.user,
            reporting_period=ReportingPeriodFactory(
                start_date=datetime.datetime(2015, 11, 2)
            ),
            submitted=False
        )
        self.timecard_objects.append([
            TimecardObjectFactory(
                timecard=timecard_unsubmit,
                project=self.billable_project,
                hours_spent=10,
            ),
        ])

        response = client(self).get(reverse('HoursByQuarter')).data
        self.assertEqual(len(self.timecard_objects), 3)
        self.assertEqual(response[0]['total'], 20)

    def test_hours_by_quarter_by_user(self):
        response = client(self).get(reverse('HoursByQuarterByUser')).data
        self.assertEqual(len(response), 1)
        row = response[0]
        self.assertEqual(row['username'], str(self.user))
        self.assertEqual(row['billable'], 15)
        self.assertEqual(row['nonbillable'], 5)
        self.assertEqual(row['total'], 20)
        self.assertEqual(row['year'], 2016)
        self.assertEqual(row['quarter'], 1)

    def test_hours_by_quarter_by_user_with_unsubmitted_timecards(self):
        """ Check that unsubmitted timecards are not counted  """
        # add one unsubmitted timecard + one additional submitted one
        timecard_unsubmit = TimecardFactory(
            user=self.user,
            reporting_period=ReportingPeriodFactory(
                start_date=datetime.datetime(2015, 11, 2)
            ),
            submitted=False
        )
        self.timecard_objects.append([
            TimecardObjectFactory(
                timecard=timecard_unsubmit,
                project=self.billable_project,
                hours_spent=10,
            ),
        ])

        timecard_submit = TimecardFactory(
            user=self.user,
            reporting_period=ReportingPeriodFactory(
                start_date=datetime.datetime(2015, 11, 3)
            ),
            submitted=True
        )
        self.timecard_objects.append([
            TimecardObjectFactory(
                timecard=timecard_submit,
                project=self.billable_project,
                hours_spent=40,
            ),
        ])

        response = client(self).get(reverse('HoursByQuarterByUser')).data
        row = response[0]

        self.assertEqual(len(self.timecard_objects), 4)
        self.assertEqual(row['total'], 60)

class ReportingPeriodList(WebTest):
    fixtures = ['tock/fixtures/prod_user.json',
            'projects/fixtures/projects.json',
            'hours/fixtures/timecards.json']


    def test_ReportingPeriodList_json(self):
        """ Check that the reporting periods are listed """
        res = client(self).get(reverse('ReportingPeriodList')).data
        self.assertEqual(res.json['count'], 1)

    def test_ReportingPeriodList_json(self):
        """ Check that the ReportingPeriodList is empty when all users
        have filled out thier time cards"""
        reporting_periods = client(self).get(reverse('ReportingPeriodList')).data
        start_date = reporting_periods[0]['start_date']
        res = client(self).get(reverse(
                'ReportingPeriodAudit',
                kwargs={'reporting_period_start_date': start_date}
            )
        ).data
        self.assertEqual(len(res), 0)

    def test_ReportingPeriodList_json_missing_timesheet(self):
        """ Check that the ReportingPeriodList shows users that have missing
        time cards """
        # Create a user
        self.regular_user = get_user_model().objects.create(
            username='new.user')
        userdata = UserData(user=self.regular_user)
        userdata.save()

        reporting_periods = client(self).get(reverse('ReportingPeriodList')).data
        start_date = reporting_periods[0]['start_date']
        res = client(self).get(reverse(
                'ReportingPeriodAudit',
                kwargs={'reporting_period_start_date': start_date}
            )
        ).data
        self.assertEqual(len(res), 1)

    def test_ReportingPeriodList_json_no_longer_employed(self):
        """ Check that the ReportingPeriodList shows users that have missing
        time cards """
        # Create a user, but set the user as unemployed
        self.regular_user = get_user_model().objects.create(
            username='new.user')
        userdata = UserData(user=self.regular_user)
        userdata.current_employee = False
        userdata.save()

        reporting_periods = client(self).get(reverse('ReportingPeriodList')).data
        start_date = reporting_periods[0]['start_date']
        res = client(self).get(reverse(
                'ReportingPeriodAudit',
                kwargs={'reporting_period_start_date': start_date}
            )
        ).data
        self.assertEqual(len(res), 0)
