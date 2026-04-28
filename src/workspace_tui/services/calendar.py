from dataclasses import dataclass, field
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from loguru import logger

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.base import BaseService

CACHE_PREFIX = "calendar:"
TTL_EVENTS = 300
TTL_CALENDARS = 600


@dataclass
class CalendarEvent:
    event_id: str
    summary: str
    start: str
    end: str
    location: str = ""
    description: str = ""
    attendees: list[str] = field(default_factory=list)
    meet_link: str = ""
    calendar_id: str = ""
    all_day: bool = False
    html_link: str = ""


@dataclass
class CalendarInfo:
    calendar_id: str
    summary: str
    primary: bool = False


class CalendarService(BaseService):
    def __init__(self, credentials, cache: CacheManager) -> None:
        super().__init__(cache=cache)
        self._service = build("calendar", "v3", credentials=credentials)
        self._credentials = credentials

    def list_calendars(self) -> list[CalendarInfo]:
        def fetch():
            result = self._retry(lambda: self._service.calendarList().list().execute())
            return [
                CalendarInfo(
                    calendar_id=cal["id"],
                    summary=cal.get("summary", ""),
                    primary=cal.get("primary", False),
                )
                for cal in result.get("items", [])
            ]

        return self._cached(f"{CACHE_PREFIX}calendars", ttl=TTL_CALENDARS, fetch=fetch)

    def list_events(
        self,
        calendar_id: str = "primary",
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 100,
    ) -> list[CalendarEvent]:
        if time_min is None:
            time_min = datetime.now()
        if time_max is None:
            time_max = time_min + timedelta(days=30)

        cache_key = (
            f"{CACHE_PREFIX}events:{calendar_id}:{time_min.isoformat()}:{time_max.isoformat()}"
        )

        def fetch():
            result = self._retry(
                lambda: (
                    self._service.events()
                    .list(
                        calendarId=calendar_id,
                        timeMin=time_min.isoformat() + "Z",
                        timeMax=time_max.isoformat() + "Z",
                        maxResults=max_results,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )
            )
            return [self._parse_event(item) for item in result.get("items", [])]

        return self._cached(cache_key, ttl=TTL_EVENTS, fetch=fetch)

    def get_event(self, calendar_id: str, event_id: str) -> CalendarEvent:
        result = self._retry(
            lambda: self._service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        )
        return self._parse_event(result)

    def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        location: str = "",
        description: str = "",
        attendees: list[str] | None = None,
        calendar_id: str = "primary",
    ) -> str:
        event_body: dict = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": "Europe/Rome"},
            "end": {"dateTime": end, "timeZone": "Europe/Rome"},
        }
        if location:
            event_body["location"] = location
        if description:
            event_body["description"] = description
        if attendees:
            event_body["attendees"] = [{"email": a} for a in attendees]

        result = self._retry(
            lambda: self._service.events().insert(calendarId=calendar_id, body=event_body).execute()
        )
        self._cache.invalidate_prefix(CACHE_PREFIX)
        logger.info("Event created: {}", result.get("id"))
        return result["id"]

    def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        **updates,
    ) -> None:
        existing = self.get_event(calendar_id, event_id)
        event_body: dict = {"summary": updates.get("summary", existing.summary)}

        if "start" in updates:
            event_body["start"] = {"dateTime": updates["start"], "timeZone": "Europe/Rome"}
        if "end" in updates:
            event_body["end"] = {"dateTime": updates["end"], "timeZone": "Europe/Rome"}
        if "location" in updates:
            event_body["location"] = updates["location"]
        if "description" in updates:
            event_body["description"] = updates["description"]

        self._retry(
            lambda: (
                self._service.events()
                .update(calendarId=calendar_id, eventId=event_id, body=event_body)
                .execute()
            )
        )
        self._cache.invalidate_prefix(CACHE_PREFIX)
        logger.info("Event {} updated", event_id)

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        self._retry(
            lambda: (
                self._service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            )
        )
        self._cache.invalidate_prefix(CACHE_PREFIX)
        logger.info("Event {} deleted", event_id)

    def _parse_event(self, data: dict) -> CalendarEvent:
        start = data.get("start", {})
        end = data.get("end", {})
        all_day = "date" in start

        return CalendarEvent(
            event_id=data.get("id", ""),
            summary=data.get("summary", "(senza titolo)"),
            start=start.get("dateTime", start.get("date", "")),
            end=end.get("dateTime", end.get("date", "")),
            location=data.get("location", ""),
            description=data.get("description", ""),
            attendees=[a.get("email", "") for a in data.get("attendees", [])],
            meet_link=data.get("hangoutLink", ""),
            calendar_id=data.get("organizer", {}).get("email", ""),
            all_day=all_day,
            html_link=data.get("htmlLink", ""),
        )
