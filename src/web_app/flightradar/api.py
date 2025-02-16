import json
import logging
from urllib.request import urlopen, Request

from .coordinates import Area
from .models.airport import Airport
from .models.flight import (BriefFlight, DetailedFlight,
                                       flights_to_json)
from .models.operator import Operator

FLIGHTS_API_PATTERN = ('https://data-live.flightradar24.com/zones'
                       '/fcgi/feed.js?bounds={},{},{},{}'
                       '&faa=1&mlat=1&flarm=1&adsb=1&gnd=1&air=1'
                       '&estimated=1&maxage=14400&gliders=0&stats=1')
                    #    '&estimated=1&maxage=14400&gliders=1&stats=1')
FLIGHT_API_PATTERN = ('https://data-live.flightradar24.com/clickhandler/'
                      '?version=1.5&flight={}')
SEARCH_API_PATTERN = ('https://www.flightradar24.com/v1/search/web/find?'
                      'query={}&limit={}')
HEADERS = {'Connection': 'keep-alive',
           'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; '
                          'x64) AppleWebKit/537.36 (KHTML, '
                          'like Gecko) Chrome')}

SEARCH_TYPES = {'airport': Airport,
                'live': BriefFlight,
                'operator': Operator}


class API:
    """Main API class for FlightRadar24 interaction."""
    def __init__(self):
        self.logger = logging.getLogger('API')
        self.logger.setLevel(logging.ERROR)
        log_handler = logging.StreamHandler()
        log_handler.setLevel(logging.ERROR)
        log_fmt = logging.Formatter('[{name}]: {message}\n', style='{')
        log_handler.setFormatter(log_fmt)
        self.logger.addHandler(log_handler)

    def get_area(self, area: Area, VERBOSE=False):
        """Returns all available flights within the specified area."""
        self.logger.info('Getting flights in [{}]'.format(area))
        req = Request(FLIGHTS_API_PATTERN.format(*area),
                      headers=HEADERS)
        if VERBOSE:
            print(FLIGHTS_API_PATTERN.format(*area), flush=True)
        return flights_to_json(self.parse_flights(
            json.loads(urlopen(req).read().decode())))

    @staticmethod
    def parse_flights(data: dict):
        """Finds all flights in the response and builds their instances."""
        result = [BriefFlight.create(key, data[key])
                  for key in data if isinstance(data[key], list)]

        return result


    def get_flight(self, flight_id: str, RAW=False) -> DetailedFlight:
        """Gets more detailed info about the specified flight."""
        self.logger.info('Getting info for flight {}'.format(flight_id))
        req = Request(FLIGHT_API_PATTERN.format(flight_id),
                      headers=HEADERS)
        if RAW:
            print(FLIGHT_API_PATTERN.format(flight_id))
            return json.loads(urlopen(req).read().decode())
        else:
            try:
                return DetailedFlight.create(json.loads(urlopen(req).read().decode()))
            except KeyError as e:
                print(f'KeyError: {e}')
                print(FLIGHT_API_PATTERN.format(flight_id))


    def get_search_results(self, query: str, limit: int):
        """Retrieves search results for specified query."""
        self.logger.info('Processing search request: {}'.format(query))
        req = Request(SEARCH_API_PATTERN.format(query, limit),
                      headers=HEADERS)
        # print(SEARCH_API_PATTERN.format(query, limit))
        return json.loads(urlopen(req).read().decode())['results']

    def search(self, query: str, limit: int = 10):
        return ((SEARCH_TYPES[result['type']].create_from_search(
            res_id=result.get('id'),
            res_name=result.get('name'),
            res_label=result.get('label'),
            **result), result['type'])
                for result in self.get_search_results(query, limit)
                if result['type'] not in ('schedule', 'aircraft', 'operator'))
