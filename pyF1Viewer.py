import requests, json, re, os.path, time
from subprocess import call


class F1TVApp:
    def __init__(self):
        self.f1api = "https://api.formula1.com/v2/"
        self.f1tvapi = "https://f1tv.formula1.com/2.0/R/ENG/BIG_SCREEN_HLS/"
        self.apiKey = None
        self.headers = {"User-Agent": "RaceControl"}
        self.ascendontoken = None
        while True:
            self.mainpage()

    def get_api_key(self):
        # Download script from f1tv site
        r = requests.get("https://account.formula1.com/scripts/main.min.js")
        # Use regex to extract apikey
        self.apiKey = re.findall('apikey: *"(.*?)"', r.text)[0]

    def login(self, username, password):
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
        # Method to check if contendId has additional streams (IE: Onboards, PLC, Data)
        url = f"{self.f1tvapi}ALL/CONTENT/VIDEO/{contentId}/F1_TV_Pro_Monthly/14"
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
        meeting_data = requests.get(
            f"{self.f1tvapi}ALL/PAGE/SANDWICH/F1_TV_Pro_Monthly/14?meetingId={meetingid}&title=weekend-sessions"
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
        year_data = requests.get(
            f"{self.f1tvapi}ALL/PAGE/SEARCH/VOD/F1_TV_Pro_Monthly/14?filter_objectSubtype=Meeting&filter_season={year}&filter_fetchAll=Y&filter_orderByFom=Y"
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
    
    #Archive Related Methods
    def archive_year(self, pageId):
        url = f"{self.f1tvapi}ALL/PAGE/{pageId}/F1_TV_Pro_Monthly/2"
        archive_year_data = requests.get(url).json()
        #Build menu for year's different categories
        counter = 1
        for container in archive_year_data['resultObj']['containers']:
            if len(container['retrieveItems']['resultObj']) > 0:
                print(f"{counter}. {container['metadata']['label']}")
            counter += 1
        #Take input and decrement by 1 to get the right one.
        user_input = int(input("Choice> "))-1

        #Build menu of selection's content
        counter = 1
        for container in archive_year_data['resultObj']['containers'][user_input]['retrieveItems']['resultObj']['containers']:
            print(f"{counter}. {container['id']} - {container['metadata']['title']}")
            counter += 1
        #Take input and decrement by 1 to get the right one.
        previous_user_input = user_input
        user_input = int(input("Choice> "))-1
        contentId = archive_year_data['resultObj']['containers'][previous_user_input]['retrieveItems']['resultObj']['containers'][user_input]['id']
        self.check_additional_streams(contentId)

    def archive_year_block(self, collectionId, type="EXTCOLLECTION"):
        if type != "EXTCOLLECTION":
            url = f"{self.f1tvapi}ALL/PAGE/SEARCH/VOD/F1_TV_Pro_Monthly/14"
            archive_years = requests.get(url, params=collectionId).json()
        else:
            url = f"{self.f1tvapi}ALL/PAGE/EXTCOLLECTION/{collectionId}/F1_TV_Pro_Monthly/2"
            archive_years = requests.get(url).json()
        #Build menu for archive block's years
        counter = 1
        for year in archive_years['resultObj']['containers']:
            if type == "SEARCH":
                print(f"{counter}. {year['metadata']['title']}")
            else:
                try:
                    print(f"{counter}. {year['metadata']['season']}")
                except:
                    print(f"{counter}. {year['metadata']['title']}")
            counter += 1
        #Take input and decrement by 1 to get the right one.
        user_input = int(input("Choice> "))-1
        try:
            pageId = archive_years['resultObj']['containers'][user_input]['actions'][0]['uri'].split("ALL/PAGE/")[1].split("/")[0]
            self.archive_year(pageId)
        except:
            #If we've hit this it's probably just directly a link to a season review
            self.check_additional_streams(archive_years['resultObj']['containers'][user_input]['id'])


    def archive(self):
        archive_data = requests.get(f"{self.f1tvapi}ALL/PAGE/493/F1_TV_Pro_Monthly/14").json()

        #Print out all archive blocks and give users a choice
        counter = 1
        for container in archive_data['resultObj']['containers']:
            if container['metadata']['label'] != None and len(container['retrieveItems']['resultObj']) > 0:
                print(f"{counter}. {container['metadata']['label']}")
            counter += 1
        #Take input and decrement by 1 to get the right one.
        user_input = int(input("Choice> "))-1
        collectionId = archive_data['resultObj']['containers'][user_input]['retrieveItems']['uriOriginal'].split("/TRAY/EXTCOLLECTION/")[1]
        self.archive_year_block(collectionId)
    
    #"Shows"/"Documentaries" Related Functions

    def shows_documentaries(self, pageId):
        shows_data = requests.get(f"{self.f1tvapi}ALL/PAGE/{pageId}/F1_TV_Pro_Monthly/14").json()

        #Print out all archive blocks and give users a choice
        counter = 1
        for container in shows_data['resultObj']['containers']:
            if container['metadata']['label'] != None and len(container['retrieveItems']['resultObj']) > 0:
                print(f"{counter}. {container['metadata']['label']}")
            else:
                #Combine the names of all shows under this unnamed block
                combined = ""
                try:
                    for item in container['retrieveItems']['resultObj']['containers']:
                        combined += item['metadata']['title']+", "
                    combined = combined[:-2]
                except:
                    combined = "None"
                print(f"{counter}. {combined}")
            counter += 1
        #Take input and decrement by 1 to get the right one.
        user_input = int(input("Choice> "))-1
        try:
            collectionId = shows_data['resultObj']['containers'][user_input]['retrieveItems']['uriOriginal'].split("/TRAY/EXTCOLLECTION/")[1]
            self.archive_year_block(collectionId)
        except:
            #Since that didn't work we need to handle this differently
            #Use archive_year_block with some hackers
            params = {}
            #Generate params from uriOriginal
            original_params = shows_data['resultObj']['containers'][user_input]['retrieveItems']['uriOriginal'].split("?")[1].split("&")
            for original_param in original_params:
                params[original_param.split("=")[0]] = original_param.split("=")[1]
            self.archive_year_block(params, "SEARCH")

    def mainpage(self):
        print("1. Login")
        print("2. Year Choice")
        print("3. Archive")
        print("4. Shows")
        print("5. Documentaries")
        user_input = int(input("Choice> "))
        if user_input == 1:
            self.get_api_key()
            self.login(input("Username: "), input("Password: "))
        elif user_input == 2:
            user_input = int(input("Year Choice> "))
            self.year_content(user_input)
        elif user_input == 3:
            self.archive()
        elif user_input == 4:
            self.shows_documentaries(410)
        elif user_input == 5:
            self.shows_documentaries(413)


f1tvapp = F1TVApp()
