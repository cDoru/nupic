# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2013, Numenta, Inc.  Unless you have purchased from
# Numenta, Inc. a separate commercial license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------


from base import *
import datetime
import time
from scalar import ScalarEncoder
import numpy

from nupic.data import SENTINEL_VALUE_FOR_MISSING_DATA

############################################################################
class DateEncoder(Encoder):
  """A date encoder encodes a date according to encoding parameters
  specified in its constructor.
  The input to a date encoder is a datetime.datetime object. The output
  is the concatenation of several sub-encodings, each of which encodes
  a different aspect of the date. Which sub-encodings are present, and
  details of those sub-encodings, are specified in the DateEncoder
  constructor.

  Each parameter describes one attribute to encode. By default, the attribute
  is not encoded.

  season (season of the year; units = day):
    (int) width of attribute; default radius = 91.5 days (1 season)
    (tuple)  season[0] = width; season[1] = radius

  dayOfWeek (monday = 0; units = day)
    (int) width of attribute; default radius = 1 day
    (tuple) dayOfWeek[0] = width; dayOfWeek[1] = radius

  weekend (boolean: 0, 1)
    (int) width of attribute

  holiday (boolean: 0, 1)
    (int) width of attribute

  timeOfday (midnight = 0; units = hour)
    (int) width of attribute: default radius = 4 hours
    (tuple) timeOfDay[0] = width; timeOfDay[1] = radius





  """
  ############################################################################
  def __init__(self, season=0, dayOfWeek=0, weekend=0, holiday=0, timeOfDay=0, customDays=0,
                name = ''):

    self.width = 0
    self.description = []
    self.name = name

    # This will contain a list of (name, encoder, offset) tuples for use by
    #  the decode() method
    self.encoders = []

    self.seasonEncoder = None
    if season != 0:
      # Ignore leapyear differences -- assume 366 days in a year
      # Radius = 91.5 days = length of season
      # Value is number of days since beginning of year (0 - 355)
      if hasattr(season, "__getitem__"):
        w = season[0]
        radius = season[1]
      else:
        w = season
        radius = 91.5

      self.seasonEncoder = ScalarEncoder(w = w, minval=0, maxval=366,
                                         radius=radius, periodic=True,
                                         name="season")
      self.seasonOffset = self.width
      self.width += self.seasonEncoder.getWidth()
      self.description.append(("season", self.seasonOffset))
      self.encoders.append(("season", self.seasonEncoder, self.seasonOffset))


    self.dayOfWeekEncoder = None
    if dayOfWeek != 0:
      # Value is day of week (floating point)
      # Radius is 1 day
      if hasattr(dayOfWeek, "__getitem__"):
        w = dayOfWeek[0]
        radius = dayOfWeek[1]
      else:
        w = dayOfWeek
        radius = 1
      self.dayOfWeekEncoder = ScalarEncoder(w = w, minval=0, maxval=7,
                                            radius=radius, periodic=True,
                                            name="day of week")
      self.dayOfWeekOffset = self.width
      self.width += self.dayOfWeekEncoder.getWidth()
      self.description.append(("day of week", self.dayOfWeekOffset))
      self.encoders.append(("day of week", self.dayOfWeekEncoder, self.dayOfWeekOffset))

    self.weekendEncoder = None
    if weekend != 0:
      # Binary value. Not sure if this makes sense. Also is somewhat redundant
      #  with dayOfWeek
      #Append radius if it was not provided
      if not hasattr(weekend, "__getitem__"):
        weekend = (weekend,1)
      self.weekendEncoder = ScalarEncoder(w = weekend[0], minval = 0, maxval=1,
                                          periodic=False, radius=weekend[1],
                                          name="weekend")
      self.weekendOffset = self.width
      self.width += self.weekendEncoder.getWidth()
      self.description.append(("weekend", self.weekendOffset))
      self.encoders.append(("weekend", self.weekendEncoder, self.weekendOffset))

    #Set up custom days encoder, first argument in tuple is width
    #second is either a single day of the week or a list of the days
    #you want encoded as ones.
    self.customDaysEncoder = None
    if customDays !=0:
      customDayEncoderName = ""
      daysToParse = []
      assert len(customDays)==2, "Please provide a w and the desired days"
      if isinstance(customDays[1], list):
        for day in customDays[1]:
          customDayEncoderName+=str(day)+" "
        daysToParse=customDays[1]
      elif isinstance(customDays[1], str):
        customDayEncoderName+=customDays[1]
        daysToParse = [customDays[1]]
      else:
        assert False, "You must provide either a list of days or a single day"
      #Parse days
      self.customDays = []
      for day in daysToParse:
        if(day.lower() in ["mon","monday"]):
          self.customDays+=[0]
        elif day.lower() in ["tue","tuesday"]:
          self.customDays+=[1]
        elif day.lower() in ["wed","wednesday"]:
          self.customDays+=[2]
        elif day.lower() in ["thu","thursday"]:
          self.customDays+=[3]
        elif day.lower() in ["fri","friday"]:
          self.customDays+=[4]
        elif day.lower() in ["sat","saturday"]:
          self.customDays+=[5]
        elif day.lower() in ["sun","sunday"]:
          self.customDays+=[6]
        else:
          assert False, "Unable to understand %s as a day of week" % str(day)
      self.customDaysEncoder = ScalarEncoder(w=customDays[0], minval = 0, maxval=1,
                                            periodic=False, radius=1,
                                            name=customDayEncoderName)
      self.customDaysOffset = self.width
      self.width += self.customDaysEncoder.getWidth()
      self.description.append(("customdays", self.customDaysOffset))
      self.encoders.append(("customdays", self.customDaysEncoder, self.customDaysOffset))

    self.holidayEncoder = None
    if holiday != 0:
      # A "continuous" binary value. = 1 on the holiday itself and smooth ramp
      #  0->1 on the day before the holiday and 1->0 on the day after the holiday.
      self.holidayEncoder = ScalarEncoder(w = holiday, minval = 0, maxval=1,
                                          periodic=False, radius=1,
                                          name="holiday")
      self.holidayOffset = self.width
      self.width += self.holidayEncoder.getWidth()
      self.description.append(("holiday", self.holidayOffset))
      self.encoders.append(("holiday", self.holidayEncoder, self.holidayOffset))

    self.timeOfDayEncoder = None
    if timeOfDay != 0:
      # Value is time of day in hours
      # Radius = 4 hours, e.g. morning, afternoon, evening, early night,
      #  late night, etc.
      if hasattr(timeOfDay, "__getitem__"):
        w = timeOfDay[0]
        radius = timeOfDay[1]
      else:
        w = timeOfDay
        radius = 4
      self.timeOfDayEncoder = ScalarEncoder(w = w, minval=0, maxval=24,
                              periodic=True, radius=radius, name="time of day")
      self.timeOfDayOffset = self.width
      self.width += self.timeOfDayEncoder.getWidth()
      self.description.append(("time of day", self.timeOfDayOffset))
      self.encoders.append(("time of day", self.timeOfDayEncoder, self.timeOfDayOffset))

  ############################################################################
  def getWidth(self):
    return self.width

  ############################################################################
  def getScalarNames(self, parentFieldName=''):
    """ See method description in base.py """

    names = []

    # This forms a name which is the concatenation of the parentFieldName
    #   passed in and the encoder's own name.
    def _formFieldName(encoder):
      if parentFieldName == '':
        return encoder.name
      else:
        return '%s.%s' % (parentFieldName, encoder.name)

    # -------------------------------------------------------------------------
    # Get the scalar values for each sub-field
    if self.seasonEncoder is not None:
      names.append(_formFieldName(self.seasonEncoder))

    if self.dayOfWeekEncoder is not None:
      names.append(_formFieldName(self.dayOfWeekEncoder))

    if self.customDaysEncoder is not None:
      names.append(_formFieldName(self.customDaysEncoder))

    if self.weekendEncoder is not None:
      names.append(_formFieldName(self.weekendEncoder))

    if self.holidayEncoder is not None:
      names.append(_formFieldName(self.holidayEncoder))

    if self.timeOfDayEncoder is not None:
      names.append(_formFieldName(self.timeOfDayEncoder))

    return names

  ############################################################################
  def getEncodedValues(self, input):
    """ See method description in base.py """

    if input == SENTINEL_VALUE_FOR_MISSING_DATA:
      return numpy.array([None])

    assert isinstance(input, datetime.datetime)
    values = []

    # -------------------------------------------------------------------------
    # Get the scalar values for each sub-field
    timetuple = input.timetuple()
    timeOfDay = timetuple.tm_hour + float(timetuple.tm_min)/60.0

    if self.seasonEncoder is not None:
      dayOfYear = timetuple.tm_yday
      # input.timetuple() computes the day of year 1 based, so convert to 0 based
      values.append(dayOfYear-1)

    if self.dayOfWeekEncoder is not None:
      dayOfWeek = timetuple.tm_wday #+ timeOfDay / 24.0
      values.append(dayOfWeek)

    if self.weekendEncoder is not None:
      # saturday, sunday or friday evening
      if timetuple.tm_wday == 6 or timetuple.tm_wday == 5 \
          or (timetuple.tm_wday == 4 and timeOfDay > 18):
        weekend = 1
      else:
        weekend = 0
      values.append(weekend)

    if self.customDaysEncoder is not None:
      if timetuple.tm_wday in self.customDays:
        customDay = 1
      else:
        customDay = 0
      values.append(customDay)
    if self.holidayEncoder is not None:
      # A "continuous" binary value. = 1 on the holiday itself and smooth ramp
      #  0->1 on the day before the holiday and 1->0 on the day after the holiday.
      # Currently the only holiday we know about is December 25
      # holidays is a list of holidays that occur on a fixed date every year
      holidays = [(12, 25)]
      val = 0
      for h in holidays:
        # hdate is midnight on the holiday
        hdate = datetime.datetime(timetuple.tm_year, h[0], h[1], 0, 0, 0)
        if input > hdate:
          diff = input - hdate
          if diff.days == 0:
            # return 1 on the holiday itself
            val = 1
            break
          elif diff.days == 1:
            # ramp smoothly from 1 -> 0 on the next day
            val = 1.0 - (float(diff.seconds) / (86400))
            break
        else:
          diff = hdate - input
          if diff.days == 0:
            # ramp smoothly from 0 -> 1 on the previous day
            val = 1.0 - (float(diff.seconds) / 86400)

      values.append(val)

    if self.timeOfDayEncoder is not None:
      values.append(timeOfDay)

    return values

  ############################################################################
  def getScalars(self, input):
    """ See method description in base.py

    Parameters:
    -----------------------------------------------------------------------
    input:          A datetime object representing the time being encoded

    Returns:        A numpy array of the corresponding scalar values in
                    the following order:

                    [season, dayOfWeek, weekend, holiday, timeOfDay]

                    Note: some of these fields might be omitted if they were not
                    specified in the encoder
    """
    return numpy.array(self.getEncodedValues(input))

  ############################################################################
  def getBucketIndices(self, input):
    """ See method description in base.py """

    if input == SENTINEL_VALUE_FOR_MISSING_DATA:
      # Encoder each sub-field
      return [None] * len(self.encoders)

    else:
      assert isinstance(input, datetime.datetime)

      # Get the scalar values for each sub-field
      scalars = self.getScalars(input)

      # Encoder each sub-field
      result = []
      for i in xrange(len(self.encoders)):
        (name, encoder, offset) = self.encoders[i]
        result.extend(encoder.getBucketIndices(scalars[i]))
      return result

  ############################################################################
  def encodeIntoArray(self, input, output):
    """ See method description in base.py """

    if input == SENTINEL_VALUE_FOR_MISSING_DATA:
      output[0:] = 0
    else:
      assert isinstance(input, datetime.datetime)

      # Get the scalar values for each sub-field
      scalars = self.getScalars(input)

      # Encoder each sub-field
      for i in xrange(len(self.encoders)):
        (name, encoder, offset) = self.encoders[i]
        encoder.encodeIntoArray(scalars[i], output[offset:])


  ############################################################################
  def getDescription(self):
    return self.description




############################################################################
def testDateEncoder():

  print "Testing DateEncoder...",

  # 3 bits for season, 1 bit for day of week, 2 for weekend, 5 for time of day
  e = DateEncoder(season=3, dayOfWeek=1, weekend=3, timeOfDay=5)
  assert e.getDescription() == [("season", 0), ("day of week", 12),
                                ("weekend", 19), ("time of day", 25)]

  # in the middle of fall, thursday, not a weekend, afternoon
  d = datetime.datetime(2010, 11, 4, 14, 55)
  bits = e.encode(d)

  # season is aaabbbcccddd (1 bit/month)
  seasonExpected = [0,0,0,0,0,0,0,0,0,1,1,1]

  # should be 000000000111 (centered on month 11)
  # week is MTFTFSS
  # contrary to localtime documentation, Monaday = 0 (for python
  #  datetime.datetime.timetuple()
  dayOfWeekExpected = [0,0,0,1,0,0,0]

  # not a weekend, so it should be "False"
  weekendExpected = [1,1,1,0,0,0]

  # time of day has radius of 4 hours and w of 5 so each bit = 240/5 min = 48min
  # 14:55 is minute 14*60 + 55 = 895; 895/48 = bit 18.6
  # should be 30 bits total (30 * 48 minutes = 24 hours)
  timeOfDayExpected = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0]
  expected = numpy.array(seasonExpected + dayOfWeekExpected + weekendExpected \
                          + timeOfDayExpected, dtype=defaultDtype)
  assert (expected == bits).all()


  print
  e.pprintHeader()
  e.pprint(bits)
  print

  # MISSING VALUES
  mvOutput = e.encode(SENTINEL_VALUE_FOR_MISSING_DATA)
  assert sum(mvOutput) == 0


  # Check decoding
  decoded = e.decode(bits)
  print decoded
  (fieldsDict, fieldNames) = decoded
  assert len(fieldsDict) == 4
  (ranges, desc) = fieldsDict['season']
  assert len(ranges) == 1 and numpy.array_equal(ranges[0], [305, 305])
  (ranges, desc) = fieldsDict['time of day']
  assert len(ranges) == 1 and numpy.array_equal(ranges[0], [14.4, 14.4])
  (ranges, desc) = fieldsDict['day of week']
  assert len(ranges) == 1 and numpy.array_equal(ranges[0], [3, 3])
  (ranges, desc) = fieldsDict['weekend']
  assert len(ranges) == 1 and numpy.array_equal(ranges[0], [0, 0])
  print "decodedToStr=>", e.decodedToStr(decoded)

  # Check topDownCompute
  topDown = e.topDownCompute(bits)
  topDownValues = numpy.array([elem.value for elem in topDown])
  errs = topDownValues - numpy.array([320.25, 3.5, .167, 14.8])
  assert (errs.max() < 0.001)


  # Check bucket index support
  bucketIndices = e.getBucketIndices(d)
  print "bucket indices:", bucketIndices
  topDown = e.getBucketInfo(bucketIndices)

  topDownValues = numpy.array([elem.value for elem in topDown])
  errs = topDownValues - numpy.array([320.25, 3.5, .167, 14.8])
  assert (errs.max() < 0.001)

  encodings = []
  for x in topDown:
    encodings.extend(x.encoding)
  assert (encodings == expected).all()



  # look at holiday more carefully because of the smooth transition
  e = DateEncoder(holiday=5)
  holiday = numpy.array([0,0,0,0,0,1,1,1,1,1], dtype='uint8')
  notholiday = numpy.array([1,1,1,1,1,0,0,0,0,0], dtype='uint8')
  holiday2 = numpy.array([0,0,0,1,1,1,1,1,0,0], dtype='uint8')

  d = datetime.datetime(2010, 12, 25, 4, 55)
  assert (e.encode(d) == holiday).all()

  d = datetime.datetime(2008, 12, 27, 4, 55)
  assert (e.encode(d) == notholiday).all()

  d = datetime.datetime(1999, 12, 26, 8, 00)
  assert (e.encode(d) == holiday2).all()

  d = datetime.datetime(2011, 12, 24, 16, 00)
  assert (e.encode(d) == holiday2).all()

  # Test weekend encoder
  e = DateEncoder(customDays = (21,["sat","sun","fri"]))
  mon = DateEncoder(customDays = (21,"Monday"))

  e2 = DateEncoder(weekend=(21,1))
  d = datetime.datetime(1988,5,29,20,00)
  assert numpy.equal(e.encode(d),e2.encode(d)).all()
  for i in range(300):
    d = d+datetime.timedelta(days=1)
    assert numpy.equal(e.encode(d),e2.encode(d)).all()
    print mon.decode(mon.encode(d))
    #Make sure
    if mon.decode(mon.encode(d))[0]["Monday"][0][0][0]==1.0:
       assert d.weekday()==0
    else:
       assert not (d.weekday()==0)
  print "passed"

################################################################################
if __name__=='__main__':

  # Run all tests
  testDateEncoder()