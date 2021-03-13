from subprocess import call
import json
import re
import os.path
import time
import requests


class F1TVApp:
    def __init__(self):
        """Initialising F1TVApp"""
        self.f1api = "https://api.formula1.com/v2/"
        self.f1tvapi = "https://f1tv.formula1.com/2.0/R/ENG/BIG_SCREEN_HLS/"
        self.apiKey = None
        self.headers = {"User-Agent": "RaceControl"}
        self.ascendontoken = None
        self.f1tvapi_groupId = 14
        while True:
            self.mainpage()

    def get_api_key(self):
        """Obtain F1 account api api key"""
        # Download script from f1tv site
        r = requests.get("https://account.formula1.com/scripts/main.min.js")
        # Use regex to extract apikey
        self.apiKey = re.findall('apikey: *"(.*?)"', r.text)[0]

    def login(self, username, password):
        """Logs into F1TV, stores logins for 23hours to reduce auth calls"""

        # Mostly unrelated, but we must get the users "groupId" and store it - makes little difference but can't hurt
        try:
            self.f1tvapi_groupId = requests.get(
                "https://f1tv.formula1.com/1.0/R/ENG/BIG_SCREEN_HLS/ALL/USER/LOCATION"
            ).json()["resultObj"]["userLocation"][0]["groupId"]
        except:
            pass

        login_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "RaceControl",
            "apiKey": self.apiKey,
            "Content-Type": "application/json",
        }
        data = {"Login": username, "Password": password}
        # Check if we have already stored auth
        if os.path.isfile("auth.json"):
            # Check if credentials are within the last 24 hours
            with open("auth.json") as f:
                saved_auth = json.load(f)
            # Check within 23 hours to be safe
            if saved_auth["time"] <= int(time.time()) - 82800:
                # We need to get new auth:

                print("Retrieving and storing new auth")
                r = requests.post(
                    f"{self.f1api}account/subscriber/authenticate/by-password",
                    headers=login_headers,
                    json=data,
                )
                # return the ascendontoken
                self.ascendontoken = r.json()["data"]["subscriptionToken"]
                file_data = {
                    "time": int(time.time()),
                    "token": r.json()["data"]["subscriptionToken"],
                }
                with open("auth.json", "w") as f:
                    json.dump(file_data, f)

            else:
                # Our existing token is new-enough
                print("Using existing auth")
                self.ascendontoken = saved_auth["token"]
        else:
            # We don't have any auth and so therefore must create & save it.
            print("Retrieving and storing new auth")
            r = requests.post(
                f"{self.f1api}account/subscriber/authenticate/by-password",
                headers=login_headers,
                json=data,
            )
            # return the ascendontoken
            self.ascendontoken = r.json()["data"]["subscriptionToken"]
            file_data = {
                "time": int(time.time()),
                "token": r.json()["data"]["subscriptionToken"],
            }
            with open("auth.json", "w") as f:
                json.dump(file_data, f)

    def play_content(self, contentId, channelId=None):
        """With a given contentId and optional channelId, play that by printing the url and launching mpv"""
        url = "https://f1tv.formula1.com/1.0/R/ENG/BIG_SCREEN_HLS/ALL/CONTENT/PLAY"
        params = {"contentId": contentId}
        if channelId:
            params["channelId"] = channelId
        content_headers = {**self.headers, **{"ascendontoken": self.ascendontoken}}

        r = requests.get(url, params=params, headers=content_headers)
        if r.ok:
            print("Launching mpv with stream url: " + r.json()["resultObj"]["url"])
            call(f"mpv \"{r.json()['resultObj']['url']}\"")

    def check_additional_streams(self, contentId):
        """Method to check if contendId has additional streams (IE: Onboards, PLC, Data)"""
        url = f"{self.f1tvapi}ALL/CONTENT/VIDEO/{contentId}/F1_TV_Pro_Monthly/{self.f1tvapi_groupId}"
        content_data = requests.get(url).json()

        if (
            "additionalStreams"
            in content_data["resultObj"]["containers"][0]["metadata"]
        ):
            # There are some additional streams - print them out and give a choice
            print(f"1. {contentId}/nochannel - Main Feed")
            counter = 2
            for additional_stream in content_data["resultObj"]["containers"][0][
                "metadata"
            ]["additionalStreams"]:
                # Get channel id
                channelId = (
                    additional_stream["playbackUrl"]
                    .split("CONTENT/PLAY?")[1]
                    .split("&")[0]
                    .split("=")[1]
                )
                print(
                    f"{counter}. {contentId}/{channelId} - {additional_stream['type']} - {additional_stream['title']}"
                )
                counter += 1
            # Take a user input and decrement by 2 if not 1
            user_input = int(input("Channel Choice> "))
            if user_input != 1:
                user_input -= 2
                self.play_content(
                    contentId,
                    content_data["resultObj"]["containers"][0]["metadata"][
                        "additionalStreams"
                    ][user_input]["playbackUrl"]
                    .split("CONTENT/PLAY?")[1]
                    .split("&")[0]
                    .split("=")[1],
                )
            else:
                self.play_content(contentId)
        else:
            self.play_content(contentId)

    def meeting_content(self, meetingid):
        """Get contents of a meeting (contents=session meeting=event)"""
        meeting_data = requests.get(
            f"{self.f1tvapi}ALL/PAGE/SANDWICH/F1_TV_Pro_Monthly/{self.f1tvapi_groupId}?meetingId={meetingid}&title=weekend-sessions"
        )
        # Print out all sessions of meeting
        if meeting_data.ok:
            counter = 1
            for session in meeting_data.json()["resultObj"]["containers"]:
                print(f"{counter}. {session['id']} - {session['metadata']['title']}")
                counter += 1
            # Decrement by 1 in order to get the rght one
            user_input = int(input("Session Choice> ")) - 1
            # self.play_content(meeting_data.json()['resultObj']['containers'][user_input]['id'])
            self.check_additional_streams(
                meeting_data.json()["resultObj"]["containers"][user_input]["id"]
            )

    def year_content(self, year):
        """Get all content for a given year"""
        year_data = requests.get(
            f"{self.f1tvapi}ALL/PAGE/SEARCH/VOD/F1_TV_Pro_Monthly/{self.f1tvapi_groupId}?filter_objectSubtype=Meeting&filter_season={year}&filter_fetchAll=Y&filter_orderByFom=Y"
        )
        # Print out all "meetings"
        if year_data.ok:
            counter = 1
            for meeting in year_data.json()["resultObj"]["containers"]:
                print(
                    f"{counter}. {meeting['metadata']['emfAttributes']['MeetingKey']},{meeting['id']} - {meeting['metadata']['title']}"
                )
                counter += 1
            # Decrement by 1 in order to get the rght one
            user_input = int(input("Meeting Choice> ")) - 1
            self.meeting_content(
                year_data.json()["resultObj"]["containers"][user_input]["metadata"][
                    "emfAttributes"
                ]["MeetingKey"]
            )

    # Archive Related Methods
    def archive_year(self, pageId):
        """Individual years from archive, used by archive_year_block"""
        url = (
            f"{self.f1tvapi}ALL/PAGE/{pageId}/F1_TV_Pro_Monthly/{self.f1tvapi_groupId}"
        )
        archive_year_data = requests.get(url).json()
        # Build menu for year's different categories
        counter = 1
        for container in archive_year_data["resultObj"]["containers"]:
            if len(container["retrieveItems"]["resultObj"]) > 0:
                print(f"{counter}. {container['metadata']['label']}")
            counter += 1
        # Take input and decrement by 1 to get the right one.
        user_input = int(input("Choice> ")) - 1

        # Build menu of selection's content
        counter = 1
        for container in archive_year_data["resultObj"]["containers"][user_input][
            "retrieveItems"
        ]["resultObj"]["containers"]:
            print(f"{counter}. {container['id']} - {container['metadata']['title']}")
            counter += 1
        # Take input and decrement by 1 to get the right one.
        previous_user_input = user_input
        user_input = int(input("Choice> ")) - 1
        contentId = archive_year_data["resultObj"]["containers"][previous_user_input][
            "retrieveItems"
        ]["resultObj"]["containers"][user_input]["id"]
        self.check_additional_streams(contentId)

    def archive_year_block(self, collectionId, type="EXTCOLLECTION"):
        """Used as part of the shows/archive/documentaries feature; 
        this takes "blocks" (horizontal scrollers in the UI) of the pages and spits out their data"""
        if type != "EXTCOLLECTION":
            url = f"{self.f1tvapi}ALL/PAGE/SEARCH/VOD/F1_TV_Pro_Monthly/{self.f1tvapi_groupId}"
            archive_years = requests.get(url, params=collectionId).json()
        else:
            url = f"{self.f1tvapi}ALL/PAGE/EXTCOLLECTION/{collectionId}/F1_TV_Pro_Monthly/{self.f1tvapi_groupId}"
            archive_years = requests.get(url).json()
        # Build menu for archive block's years
        counter = 1
        for year in archive_years["resultObj"]["containers"]:
            if type == "SEARCH":
                print(f"{counter}. {year['metadata']['title']}")
            else:
                try:
                    print(f"{counter}. {year['metadata']['season']}")
                except:
                    print(f"{counter}. {year['metadata']['title']}")
            counter += 1
        # Take input and decrement by 1 to get the right one.
        user_input = int(input("Choice> ")) - 1
        try:
            pageId = (
                archive_years["resultObj"]["containers"][user_input]["actions"][0][
                    "uri"
                ]
                .split("ALL/PAGE/")[1]
                .split("/")[0]
            )
            self.archive_year(pageId)
        except:
            # If we've hit this it's probably just directly a link to a season review
            self.check_additional_streams(
                archive_years["resultObj"]["containers"][user_input]["id"]
            )

    def archive(self):
        """Function allows accessing the f1tv api for the "Archive" page"""
        archive_data = requests.get(
            f"{self.f1tvapi}ALL/PAGE/493/F1_TV_Pro_Monthly/{self.f1tvapi_groupId}"
        ).json()

        # Print out all archive blocks and give users a choice
        counter = 1
        for container in archive_data["resultObj"]["containers"]:
            if (
                container["metadata"]["label"] != None
                and len(container["retrieveItems"]["resultObj"]) > 0
            ):
                print(f"{counter}. {container['metadata']['label']}")
            counter += 1
        # Take input and decrement by 1 to get the right one.
        user_input = int(input("Choice> ")) - 1
        collectionId = archive_data["resultObj"]["containers"][user_input][
            "retrieveItems"
        ]["uriOriginal"].split("/TRAY/EXTCOLLECTION/")[1]
        self.archive_year_block(collectionId)

    # "Shows"/"Documentaries" Related Functions

    def shows_documentaries(self, pageId):
        """Function allows accessing the f1tv api for the "shows" or "documentaries" pages"""
        shows_data = requests.get(
            f"{self.f1tvapi}ALL/PAGE/{pageId}/F1_TV_Pro_Monthly/{self.f1tvapi_groupId}"
        ).json()

        # Print out all archive blocks and give users a choice
        counter = 1
        for container in shows_data["resultObj"]["containers"]:
            if (
                container["metadata"]["label"] != None
                and len(container["retrieveItems"]["resultObj"]) > 0
            ):
                print(f"{counter}. {container['metadata']['label']}")
            else:
                # Combine the names of all shows under this unnamed block
                combined = ""
                try:
                    for item in container["retrieveItems"]["resultObj"]["containers"]:
                        combined += item["metadata"]["title"] + ", "
                    combined = combined[:-2]
                except:
                    combined = "None"
                print(f"{counter}. {combined}")
            counter += 1
        # Take input and decrement by 1 to get the right one.
        user_input = int(input("Choice> ")) - 1
        try:
            collectionId = shows_data["resultObj"]["containers"][user_input][
                "retrieveItems"
            ]["uriOriginal"].split("/TRAY/EXTCOLLECTION/")[1]
            self.archive_year_block(collectionId)
        except:
            # Since that didn't work we need to handle this differently
            # Use archive_year_block with some hackers
            params = {}
            # Generate params from uriOriginal
            original_params = (
                shows_data["resultObj"]["containers"][user_input]["retrieveItems"][
                    "uriOriginal"
                ]
                .split("?")[1]
                .split("&")
            )
            for original_param in original_params:
                params[original_param.split("=")[0]] = original_param.split("=")[1]
            self.archive_year_block(params, "SEARCH")

    def mainpage(self):
        menu_items = ["Login", "Year Choice", "Archive", "Shows", "Documentaries"]
        # If there is a current live session - put it on the main menu
        frontpage_url = (
            f"{self.f1tvapi}ALL/PAGE/395/F1_TV_Pro_Monthly/{self.f1tvapi_groupId}"
        )
        frontpage_data = requests.get(frontpage_url).json()
        for item in frontpage_data["resultObj"]["containers"]:
            for sub_item in item["retrieveItems"]["resultObj"]["containers"]:
                if sub_item["metadata"]["contentSubtype"] == "LIVE":
                    # This is (one of?) the currently live event(s)!
                    live_event = sub_item["id"]
                    menu_items.insert(
                        1,
                        f"{sub_item['id']} - LIVE EVENT - {sub_item['metadata']['title']}",
                    )
        counter = 1
        for menu_item in menu_items:
            print(f"{counter}. {menu_item}")
            counter += 1

        # Decrement by 1 to get the right one
        user_input = int(input("Choice> ")) - 1
        chosen_item = menu_items[user_input]
        if "LIVE EVENT" in chosen_item:
            self.check_additional_streams(chosen_item.split(" -")[0])
        elif "Login" in chosen_item:
            self.get_api_key()
            self.login(input("Username: "), input("Password: "))
        elif "Year Choice" in chosen_item:
            user_input = int(input("Year Choice> "))
            self.year_content(user_input)
        elif "Archive" in chosen_item:
            self.archive()
        elif "Shows" in chosen_item:
            self.shows_documentaries(410)
        elif "Documentaries" in chosen_item:
            self.shows_documentaries(413)


F1TVAPP = F1TVApp()
