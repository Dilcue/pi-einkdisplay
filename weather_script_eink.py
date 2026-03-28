from datetime import timezone
import datetime
import time
import requests
import RPi.GPIO as GPIO
import dateutil.parser
import sys

import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from PIL import Image, ImageDraw, ImageFont
from papirus import Papirus
from datetime import datetime


#######################
# CONSTS
#######################
LATITUDE = "YOUR_LATITUDE"
LONGITUDE = "YOUR_LONGITUDE"
PAGE_DELAY = 7
DATA_REFRESH_THRESHOLD = round(1 * 60 * 60 / PAGE_DELAY)

DISP = Papirus()

WIDTH = DISP.width
HEIGHT = DISP.height
PADDING = -2
TOP = PADDING
BOTTOM = HEIGHT - PADDING

SW1 = 21
SW2 = 16
SW3 = 20
SW4 = 19
SW5 = 26

WHITE = 1
BLACK = 0

FONT = ImageFont.truetype('./nokiafc22.ttf', 8)
HEADER_FONT = ImageFont.truetype('./nokiafc22.ttf', 12)
HUGE_FONT = ImageFont.truetype('./nokiafc22.ttf', 24)
WEATHER_FONT = ImageFont.truetype('./CD-IconsPC.ttf', 32)
BIG_WEATHER_FONT = ImageFont.truetype('./CD-IconsPC.ttf', 48)

# Secrets
OPEN_WEATHER_MAP_API_KEY = ""

#######################
# Display Switch Setup
#######################
GPIO.setmode(GPIO.BCM)
GPIO.setup(SW1, GPIO.IN)
GPIO.setup(SW2, GPIO.IN)
GPIO.setup(SW3, GPIO.IN)
GPIO.setup(SW4, GPIO.IN)
GPIO.setup(SW5, GPIO.IN)

# Draw a black filled box to clear the image.
x = 0
image = Image.new('1', DISP.size, BLACK)
draw = ImageDraw.Draw(image)
DISP.update()

########################
# Variables
########################
counter = 0
page = 0
calendarEvents = None
weatherReport = None


class WeatherReport:
    lastUpdateTime = ""
    currentTemp = ""
    currentCond = ""
    currentDesc = ""
    currentWindSpeed = ""
    currentWindDirection = ""
    currentUVIndex = ""
    currentVisibility = ""
    currentSunset = ""
    currentSunrise = ""
    currentFeelsLike = ""
    currentWeatherIcon = ""

    todayDay = ""
    todayTemp = ""
    todayCond = ""
    todayDesc = ""
    todayWeatherIcon = ""

    tomorrowDay = ""
    tomorrowTemp = ""
    tomorrowCond = ""
    tomorrowDesc = ""
    tomorrowWeatherIcon = ""

    day3Day = ""
    day3Temp = ""
    day3Cond = ""
    day3Desc = ""
    day3WeatherIcon = ""

##########################
# Weather Icon Resolution
##########################


def resolveWeatherIcon(code, isDay):
    retVal = ""

    # Clear
    if(code.startswith("01")):
        if(isDay):
            retVal = "H"
        else:
            retVal = "J"
    # Partly Cloudy
    elif(code.startswith("02") or code.startswith("04")):
        if(isDay):
            retVal = "E"
        else:
            retVal = "D"
    # Cloudy
    elif(code.startswith("03")):
        retVal = "D"
    # Rainy
    elif(code.startswith("09") or code.startswith("10")):
        retVal = "B"
    # Thunderstorms
    elif(code.startswith("11")):
        retVal = "F"
    # Snow
    elif(code.startswith("13")):
        retVal = "C"
    # Mist
    elif(code.startswith("50")):
        retVal = "G"

    return retVal

###################
# UTC to Local TMZ
###################


def localTime(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

############################
# Wind degrees to direction
############################


def windDegToDir(windDeg):
    val = int((windDeg/22.5)+.5)
    arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return arr[(val % 16)]

##############################
# Get OpenWeatherMap API data
##############################


def getWeatherData():

    weatherReport = WeatherReport()

    # try :
    weatherUrl = "https://api.openweathermap.org/data/2.5/onecall?lat=" + LATITUDE + \
        "&lon=" + LONGITUDE + "&exclude=minutely,hourly,alerts&appid=" + \
        OPEN_WEATHER_MAP_API_KEY + "&units=imperial"
    response = requests.get(weatherUrl)

    print(response.status_code)

    if(response.status_code == 200):
        resBody = response.json()

        current = resBody["current"]
        today = resBody["daily"][0]
        tomorrow = resBody["daily"][1]
        day3 = resBody["daily"][2]

        weatherReport.currentTemp = str("%.0f" % current["temp"])
        weatherReport.currentCond = current["weather"][0]["main"].capitalize()
        weatherReport.currentDesc = current["weather"][0]["description"]
        weatherReport.currentWindSpeed = str("%.0f" % current["wind_speed"])
        weatherReport.currentWindDirection = windDegToDir(current["wind_deg"])
        weatherReport.currentSunrise = localTime(datetime.utcfromtimestamp(
            current["sunrise"])).strftime("%I:%M %p")
        weatherReport.currentSunset = localTime(datetime.utcfromtimestamp(
            current["sunset"])).strftime("%I:%M %p")
        weatherReport.currentUVIndex = str(current["uvi"])
        weatherReport.currentVisibility = str(current["visibility"])
        weatherReport.currentFeelsLike = str("%.0f" % current["feels_like"])
        currentIconCode = current["weather"][0]["icon"]

        weatherReport.todayDay = localTime(datetime.utcfromtimestamp(
            today["dt"])).strftime("%a")
        weatherReport.todayTemp = str(
            "%.0f" % today["temp"]["max"]) + "/" + str("%.0f" % today["temp"]["min"])
        weatherReport.todayCond = today["weather"][0]["main"].capitalize()
        weatherReport.todayDesc = today["weather"][0]["description"]
        todayIconCode = today["weather"][0]["icon"]

        weatherReport.tomorrowDay = localTime(datetime.utcfromtimestamp(
            tomorrow["dt"])).strftime("%a")
        weatherReport.tomorrowTemp = str(
            "%.0f" % tomorrow["temp"]["max"]) + "/" + str("%.0f" % tomorrow["temp"]["min"])
        weatherReport.tomorrowCond = tomorrow["weather"][0]["main"].capitalize(
        )
        weatherReport.tomorrowDesc = tomorrow["weather"][0]["description"]
        tomorrowIconCode = tomorrow["weather"][0]["icon"]

        weatherReport.day3Day = localTime(datetime.utcfromtimestamp(
            day3["dt"])).strftime("%A")
        weatherReport.day3Temp = str("%.0f" % day3["temp"]["max"]) + \
            "/" + str("%.0f" % day3["temp"]["min"])
        weatherReport.day3Cond = day3["weather"][0]["main"].capitalize()
        weatherReport.day3Desc = day3["weather"][0]["description"]
        day3IconCode = day3["weather"][0]["icon"]

        # print(currentIconCode + ", " + todayIconCode + ", " + tomorrowIconCode)
        weatherReport.sunsetTime = current["sunset"]
        isDay = True

        if(int(time.time()) > weatherReport.sunsetTime):
            isDay = False

        weatherReport.isDay = isDay

        weatherReport.currentWeatherIcon = resolveWeatherIcon(
            currentIconCode, isDay)
        weatherReport.todayWeatherIcon = resolveWeatherIcon(
            todayIconCode, isDay)
        weatherReport.tomorrowWeatherIcon = resolveWeatherIcon(
            tomorrowIconCode, True)
        weatherReport.day3WeatherIcon = resolveWeatherIcon(day3IconCode, True)

        currentTime = datetime.now()
        weatherReport.lastUpdateTime = currentTime.strftime("%I:%M")
    # except :
        #print( "Weather call failed to update" )

    return weatherReport


###########################
# Get Google Calendar Data
###########################
def getGoogleCalendarData():

    calendarEvents = None

    # DISPlay Google Calendar Events
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file(
            'token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    calendarEvents = None
    try:
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=3, singleEvents=True,
                                              orderBy='startTime').execute()
        calendarEvents = events_result.get('items', [])
    except:
        print("Calendar call failed")

    return calendarEvents


################
# Main function
################
# Check arguments
if(len(sys.argv[1:]) != 1):
    print("Arguments are required!  In order provide: Weather API Key")
    exit()
else:
    OPEN_WEATHER_MAP_API_KEY = sys.argv[1]

# Loop de loop
while True:
    # Some screens request longer display time
    timeDelayBonus = 0

    # Draw a black filled box to clear the image.
    image = Image.new('1', DISP.size, WHITE)
    draw = ImageDraw.Draw(image)

    # Only call external services at/after threshold
    if(weatherReport is None or calendarEvents is None or counter >= DATA_REFRESH_THRESHOLD):
        if(weatherReport is None or counter >= DATA_REFRESH_THRESHOLD):
            weatherReport = getWeatherData()
        if(calendarEvents is None or counter >= DATA_REFRESH_THRESHOLD):
            calendarEvents = getGoogleCalendarData()
        # Reset refresh timer
        counter = 0

    # Create pages for Display
    if(page == 0):
        # Display current date and time
        now = datetime.now()
        currentDay = now.strftime("%A")
        currentDate = now.strftime("%B, %d %Y")
        currentTime = now.strftime("%I:%M %p")
        dayLen = len(currentDay)
        dateLen = len(currentDate)
        timeLen = len(currentTime)

        draw.text((((128-timeLen)/4), TOP + 15),
                  currentTime, font=HUGE_FONT, fill=BLACK)
        draw.text((((128-dayLen)/2), TOP + 60),
                  currentDay, font=HEADER_FONT, fill=BLACK)
        draw.text((((128-dateLen)/2.75), TOP + 75),
                  currentDate, font=HEADER_FONT, fill=BLACK)

        page += 1
    elif(page == 1):
        timeDelayBonus = 1
        # Display current weather
        draw.text((0, TOP + 2), "Right Now", font=HEADER_FONT, fill=BLACK)
        draw.text((102, TOP + 6), "(as of " + weatherReport.lastUpdateTime +
                  " update)", font=FONT, fill=BLACK)
        draw.line([(0, TOP + 16), (200, TOP + 16)], fill=BLACK)

        draw.text((0, TOP + 30), weatherReport.currentWeatherIcon,
                  font=BIG_WEATHER_FONT, fill=BLACK)

        draw.text((45, TOP + 19), weatherReport.currentTemp,
                  font=HUGE_FONT, fill=BLACK)
        draw.text((90, TOP + 22), weatherReport.currentDesc.capitalize(),
                  font=FONT, fill=BLACK)
        draw.text((90, TOP + 34), "Feels Like " +
                  weatherReport.currentFeelsLike, font=FONT, fill=BLACK)

        draw.text((45, TOP + 50), "Wind Speed: " + weatherReport.currentWindSpeed +
                  "mph " + weatherReport.currentWindDirection, font=FONT, fill=BLACK)
        draw.text((45, TOP + 60), "UV Index: " +
                  weatherReport.currentUVIndex, font=FONT, fill=BLACK)
        draw.text((45, TOP + 70), "Visibility: " +
                  weatherReport.currentVisibility, font=FONT, fill=BLACK)
        draw.text((45, TOP + 80), "Sunrise: " +
                  weatherReport.currentSunrise, font=FONT, fill=BLACK)
        draw.text((45, TOP + 90), "Sunset: " +
                  weatherReport.currentSunset, font=FONT, fill=BLACK)

        page += 1
    elif(page == 2):
        # 3-Day Forecast
        # Display today's weather
        draw.text((0, TOP), weatherReport.currentWeatherIcon,
                  font=WEATHER_FONT, fill=BLACK)
        draw.text((30, TOP + 2), "Today", font=FONT, fill=BLACK)
        draw.text((172, TOP + 2), "(" + weatherReport.todayDay + ")",
                  font=FONT, fill=BLACK)
        draw.line([(30, TOP + 12), (200, TOP + 12)], fill=BLACK)
        draw.text((30, TOP + 13), weatherReport.todayTemp,
                  font=HEADER_FONT, fill=BLACK)
        draw.text((85, TOP + 15), weatherReport.todayCond + ", " +
                  weatherReport.todayDesc, font=FONT, fill=BLACK)

        TOP += 33
        # Display tomorrow's weather
        draw.text((0, TOP), weatherReport.tomorrowWeatherIcon,
                  font=WEATHER_FONT, fill=BLACK)
        draw.text((30, TOP + 2), "Tomorrow", font=FONT, fill=BLACK)
        draw.text((172, TOP + 2), "(" + weatherReport.tomorrowDay + ")",
                  font=FONT, fill=BLACK)
        draw.line([(30, TOP + 12), (200, TOP + 12)], fill=BLACK)
        draw.text((30, TOP + 13), weatherReport.tomorrowTemp,
                  font=HEADER_FONT, fill=BLACK)
        draw.text((85, TOP + 15), weatherReport.tomorrowCond + ", " +
                  weatherReport.tomorrowDesc, font=FONT, fill=BLACK)

        TOP += 33
        # Display 3-day
        draw.text((0, TOP), weatherReport.day3WeatherIcon,
                  font=WEATHER_FONT, fill=BLACK)
        draw.text((30, TOP + 2), weatherReport.day3Day, font=FONT, fill=BLACK)
        draw.line([(30, TOP + 12), (200, TOP + 12)], fill=BLACK)
        draw.text((30, TOP + 13), weatherReport.day3Temp,
                  font=HEADER_FONT, fill=BLACK)
        draw.text((85, TOP + 15), weatherReport.day3Cond + ", " +
                  weatherReport.day3Desc, font=FONT, fill=BLACK)

        TOP = PADDING
        page += 1
    elif(page == 3):
        # Google Calendar Events
        draw.text((0, TOP + 2), "Family Calendar",
                  font=HEADER_FONT, fill=BLACK)
        draw.line([(0, TOP + 16), (200, TOP + 16)], fill=BLACK)
        y = 20
        if not calendarEvents:
            draw.text((34, 25), 'No upcoming events!', font=FONT, fill=BLACK)
        else:
            timeDelayBonus = 1
            for event in calendarEvents:
                allDay = False
                start = None
                end = None
                sameStartEndTime = False
                sameStartEndDay = False
                timeDisplay = ""
                eventSummary = event['summary']

                if(event['start'].get('dateTime') == None):
                    start = dateutil.parser.parse(event['start'].get('date'))
                    allDay = True
                else:
                    start = dateutil.parser.parse(
                        event['start'].get('dateTime'))

                if(event['end'].get('dateTime') == None):
                    end = dateutil.parser.parse(event['end'].get('date'))
                else:
                    end = dateutil.parser.parse(event['end'].get('dateTime'))

                # Check for similarities between start and end
                if(start == end):
                    sameStartEndTime = True
                elif(start.strftime("%A%B%Y") == end.strftime("%A%B%Y")):
                    sameStartEndDay = True

                # Do the formatting
                if(allDay):
                    timeDisplay += start.strftime("%a %b %d") + " (All Day)"
                elif(sameStartEndTime):
                    timeDisplay += start
                elif(sameStartEndDay):
                    timeDisplay += start.strftime("%a %b %d, %I:%M %p") + \
                        "-" + end.strftime("%I:%M %p")
                else:
                    timeDisplay += start.strftime("%a %b%d, %I:%M %p") + \
                        "-" + end.strftime("%a %b%d, %I:%M %p")

                print(str(start), str(end), str(allDay), str(
                    sameStartEndTime), str(sameStartEndDay), event['summary'])
                draw.text((30, y), timeDisplay, font=FONT, fill=BLACK)
                draw.text((0, y-13), "¿", font=WEATHER_FONT, fill=BLACK)
                y += 11
                draw.text((30, y), eventSummary, font=FONT, fill=BLACK)

                y += 16
        page = 0

    # DISPlay image.
    DISP.display(image)
    # if( page % 1 ) :
    DISP.update()
    # else :
    # DISP.partial_update()
    # DISP.show()
    time.sleep(PAGE_DELAY + timeDelayBonus)

    counter += 1
