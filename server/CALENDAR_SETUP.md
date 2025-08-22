# Google Calendar Integration Setup Guide

This guide will help you set up Google Calendar integration for Alice's tool system.

## Overview

Alice now supports complete Google Calendar integration with the following features:
- Create calendar events/meetings
- List upcoming events  
- Search for specific events
- Delete events
- Update existing events
- Swedish language support for date/time parsing
- Natural language commands in Swedish

## Prerequisites

1. **Google Cloud Console Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Google Calendar API

2. **Dependencies** (already included in requirements.txt)
   ```
   google-api-python-client
   google-auth-httplib2
   google-auth-oauthlib
   pytz
   ```

## Setup Steps

### 1. Create Google Calendar API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" > "Credentials"
3. Click "Create Credentials" > "OAuth client ID"
4. Choose "Desktop application" as application type
5. Name it (e.g., "Alice Calendar Integration")
6. Download the credentials JSON file
7. Rename it to `calendar_credentials.json`
8. Place it in `/Users/evil/Desktop/EVIL/PROJECT/Alice/alice/server/`

### 2. Enable Calendar Tools

Add Calendar tools to your `ENABLED_TOOLS` environment variable:

```bash
export ENABLED_TOOLS="PLAY,PAUSE,SET_VOLUME,CREATE_CALENDAR_EVENT,LIST_CALENDAR_EVENTS,SEARCH_CALENDAR_EVENTS,DELETE_CALENDAR_EVENT,UPDATE_CALENDAR_EVENT"
```

Or update your `.env` file:
```
ENABLED_TOOLS=PLAY,PAUSE,SET_VOLUME,CREATE_CALENDAR_EVENT,LIST_CALENDAR_EVENTS,SEARCH_CALENDAR_EVENTS,DELETE_CALENDAR_EVENT,UPDATE_CALENDAR_EVENT
```

### 3. First-time Authentication

When you first use a Calendar tool, Alice will:
1. Open your web browser to Google's OAuth consent screen
2. Ask you to authorize Alice to access your Google Calendar
3. Display an authorization URL if browser doesn't open automatically
4. Save the credentials for future use

## Available Calendar Tools

### CREATE_CALENDAR_EVENT
Create new calendar events/meetings.

**Parameters:**
- `title`: Event title (required)
- `start_time`: Start time in Swedish format (required)  
- `end_time`: End time (optional, defaults to 1 hour after start)
- `description`: Event description (optional)
- `attendees`: List of email addresses (optional)

**Swedish Examples:**
- "skapa möte imorgon kl 14:00"
- "boka tid för tandläkare på fredag kl 10:30" 
- "lägg till lunch med Jonas imorgon 12:00"
- "skapa möte 'Projektstatus' nästa måndag kl 09:00"

### LIST_CALENDAR_EVENTS
Show upcoming calendar events.

**Parameters:**
- `max_results`: Number of events to show (1-50, default: 10)
- `time_min`: Earliest time to show events from (optional)
- `time_max`: Latest time to show events until (optional)

**Swedish Examples:**
- "visa mina möten denna vecka"
- "lista kalenderhändelser"
- "vad har jag för möten imorgon"
- "visa 5 kommande händelser"

### SEARCH_CALENDAR_EVENTS
Search for specific calendar events.

**Parameters:**
- `query`: Search text to find events (required)
- `max_results`: Max number of results (1-100, default: 20)

**Swedish Examples:**
- "sök efter möte med Jonas"
- "hitta tandläkartid"
- "sök kalenderhändelse om projekt"
- "leta efter lunch möten"

### DELETE_CALENDAR_EVENT
Remove a calendar event.

**Parameters:**
- `event_id`: ID of the event to delete (required)

**Swedish Examples:**
- "ta bort mötet på fredag" (requires finding event ID first)
- "radera kalenderhändelse"
- "avboka möte med event_id abc123"

### UPDATE_CALENDAR_EVENT
Update an existing calendar event.

**Parameters:**
- `event_id`: ID of the event to update (required)
- `title`: New title (optional)
- `start_time`: New start time (optional)
- `end_time`: New end time (optional)  
- `description`: New description (optional)

**Swedish Examples:**
- "ändra mötet till kl 15:00"
- "uppdatera titel på möte"
- "flytta mötet till imorgon"
- "ändra beskrivning på kalenderhändelse"

## Swedish Date/Time Support

Alice understands Swedish date and time expressions:

### Days of the Week
- måndag, tisdag, onsdag, torsdag, fredag, lördag, söndag

### Months
- januari, februari, mars, april, maj, juni, juli, augusti, september, oktober, november, december

### Relative Dates
- **idag** - today
- **imorgon** - tomorrow  
- **igår** - yesterday

### Time Format
- **kl 14:00** - at 2:00 PM
- **14:30** - 2:30 PM
- **09:00** - 9:00 AM

### Examples
- "imorgon kl 14:00" → Tomorrow at 2:00 PM
- "fredag 16:30" → Friday at 4:30 PM  
- "måndag kl 09:00" → Monday at 9:00 AM
- "idag 12:00" → Today at 12:00 PM

## Error Handling

The Calendar integration includes comprehensive error handling for:
- Missing credentials
- Network connectivity issues
- Invalid date/time formats
- Non-existent events
- API rate limits
- Permission errors

## Troubleshooting

### "Calendar-tjänst inte tillgänglig"
- Check that `calendar_credentials.json` exists in the correct location
- Verify Google Calendar API is enabled in Google Cloud Console
- Ensure internet connection is working

### Authentication Issues
- Delete `calendar_token.pickle` to force re-authentication
- Check that OAuth consent screen is properly configured
- Verify redirect URIs in Google Cloud Console

### Date Parsing Issues
- Use format "YYYY-MM-DD HH:MM" for specific dates
- Swedish relative dates: "imorgon", "idag", "igår"
- Include "kl" before time: "imorgon kl 14:00"

### Permission Errors  
- Ensure Google Calendar API scope includes calendar access
- Check that the correct Google account is being used
- Verify calendar visibility settings

## File Structure

The Calendar integration consists of these files:

```
alice/server/
├── core/
│   ├── calendar_service.py      # Main Calendar API service
│   ├── tool_specs.py           # Pydantic models and tool definitions
│   └── tool_registry.py        # Tool executors and validation
├── calendar_credentials.json   # Google OAuth credentials (you create this)
├── calendar_token.pickle       # Stored auth token (auto-generated)
├── requirements.txt           # Updated with Calendar dependencies
└── CALENDAR_SETUP.md          # This setup guide
```

## Security Notes

- `calendar_credentials.json` contains sensitive OAuth client information
- `calendar_token.pickle` contains your access tokens
- Both files should be kept secure and not shared
- Consider adding them to `.gitignore` if using version control

## Next Steps

1. Follow the setup steps above
2. Test with a simple command: "lista kalenderhändelser"
3. Create your first event: "skapa möte imorgon kl 14:00"
4. Explore the Swedish language capabilities

The Calendar integration is now fully functional and ready to use with Alice's natural language processing system!