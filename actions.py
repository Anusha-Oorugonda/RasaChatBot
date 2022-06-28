from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from rasa_sdk import Action
from rasa_sdk.events import SlotSet

import zomatopy
import json
import pandas as pd
from city_check import check_location

from email.message import EmailMessage
from email_config import Config
from flask_mail_check import send_email

class ActionSearchRestaurants(Action):
    def name(self):
        return 'action_search_restaurants'

    def run(self, dispatcher, tracker, domain):
        config = {"user_key": "02313810ac8d6c60d73338505648f8ac"}
        loc = tracker.get_slot('location')
        cuisine = tracker.get_slot('cuisine')
        price = tracker.get_slot('price')
        global restaurants

        restaurants = self.results(loc, cuisine, price, config)
        top5 = restaurants.head(5)
        i = 1;
        # top 5 results to display
        if len(top5) > 0:
            response = 'Showing you top rated restaurants:' + "\n"
            for index, row in top5.iterrows():
                response = '\t ' + response + str(i) + '.\t  ' + str(row["restaurant_name"]) + ' in ' + str(row['restaurant_address']) + ' has been rated ' + str(row['restaurant_rating']) + "\n"
                i = i+1
            response = response + "\n\nShould i mail you the details"

        else:
            response = 'No restaurants found'

        dispatcher.utter_message(str(response))


    def results(self, loc, cuisine, price, config):
        zomato = zomatopy.initialize_app(config)
        location_detail = zomato.get_location(loc, 1)
        location_json = json.loads(location_detail)
        location_results = len(location_json['location_suggestions'])
        lat = location_json["location_suggestions"][0]["latitude"]
        lon = location_json["location_suggestions"][0]["longitude"]
        city_id = location_json["location_suggestions"][0]["city_id"]
        cuisines_dict = {'american': 1, 'chinese': 25, 'north indian': 50, 'italian': 55, 'mexican': 73,
                         'south indian': 85, 'thai': 95}

        list1 = [0, 20, 40, 60, 80]
        d = []
        df = pd.DataFrame()
        for i in list1:
            results = zomato.restaurant_search("", lat, lon, str(cuisines_dict.get(cuisine)), limit=i)

            d1 = json.loads(results)
            d = d1['restaurants']
            df1 = pd.DataFrame([{'restaurant_name': x['restaurant']['name'],
                                 'restaurant_rating': x['restaurant']['user_rating']['aggregate_rating'],
                                 'restaurant_address': x['restaurant']['location']['address'],
                                 'budget_for2people': x['restaurant']['average_cost_for_two'],
                                 'restaurant_photo': x['restaurant']['featured_image'],
                                 'restaurant_url': x['restaurant']['url']} for x in d])
            df = df.append(df1)

        def budget_group(row):
            if row['budget_for2people'] < 300:
                return 'lesser than 300'
            elif 300 <= row['budget_for2people'] < 700:
                return 'between 300 to 700'
            else:
                return 'more than 700'

        df['budget'] = df.apply(lambda row: str(budget_group(row)), axis=1)

        # sorting by review & filter by budget
        restaurant_df = df[(df.budget == price)]
        restaurant_df = restaurant_df.sort_values(['restaurant_rating'], ascending=0)
        restaurant_df = restaurant_df.drop_duplicates();
        return restaurant_df


class Check_location(Action):
    def name(self):
        return 'action_check_location'

    def run(self, dispatcher, tracker, domain):
        loc = tracker.get_slot('location')
        print("location: ", loc)
        check = check_location(loc)

        print("\n check: ", check)
        return [SlotSet('location', check['location_new']), SlotSet('location_found', check['location_f'])]


class SendMail(Action):
    def name(self):
        return 'action_email_restaurant_details'

    def run(self, dispatcher, tracker, domain):
        recipient = tracker.get_slot('email')

        top10 = restaurants.head(10)
        send_email(recipient, top10)

        dispatcher.utter_message("Have a great day!")