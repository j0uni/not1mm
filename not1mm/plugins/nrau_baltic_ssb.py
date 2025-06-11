"""NRAU-Baltic SSB Contest plugin"""

# pylint: disable=invalid-name, c-extension-no-member, unused-import

import datetime
import logging
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "#"

name = "NRAU-Baltic SSB"
cabrillo_name = "NRAU-BALTIC-SSB"
mode = "SSB"

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 2

participating_countries = [
    "ES", "JW", "JX", "LA", "LY", "OH", "OH0", "OJ0", "OX", "OY", "OZ", "SM", "TF", "YL"
]

def init_contest(self):
    """setup plugin"""
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2

def interface(self):
    """Setup user interface"""
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.show()
    self.snt_label.setText("SNT")
    self.field1.setAccessibleName("RS Sent")
    self.other_label.setText("Serial")
    self.field3.setAccessibleName("Serial Number")
    self.exch_label.setText("Country")
    self.field4.setAccessibleName("Country Code")
    self.field1.setFocus()

def reset_label(self):
    """reset label after field cleared"""

def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.receive,
        self.receive: self.other_1,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }

def set_tab_prev(self):
    """Set Shift-TAB Advances"""
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.receive: self.sent,
        self.other_1: self.receive,
        self.other_2: self.other_1,
    }

def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text()
    self.contact["NR"] = self.other_2.text()
    self.contact["Region"] = self.other_2.text()  # Use other_2 for Region

def predupe(self):
    """called after callsign entered"""

def prefill(self):
    """Fill SentNR"""
    result = self.database.get_serial()
    serial_nr = str(result.get("serial_nr", "1")).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"
    if len(self.other_1.text()) == 0:
        self.other_1.setText(serial_nr)

def points(self):
    """Calculate points"""
    if self.contact_is_dupe > 0:
        return 0

    # Get the contacted station's prefix
    result = self.cty_lookup(self.contact.get("Call", ""))
    if not result:
        return 0

    # Check frequency limits
    freq = float(self.contact.get("Freq", "0"))
    if not ((3600 <= freq <= 3650) or (3700 <= freq <= 3775) or 
            (7050 <= freq <= 7100) or (7130 <= freq <= 7200)):
        return 0  # QSO outside frequency limits

    item = result.get(next(iter(result)))
    prefix = item.get("primary_pfx", "")

    # Map special prefixes to their parent country for national competition
    if prefix in ["JW", "JX"]:
        prefix = "LA"  # Count for Norway
    elif prefix in ["OX", "OY"]:
        prefix = "OZ"  # Count for Denmark
    elif prefix in ["OH0", "OJ0"]:
        prefix = "OH"  # Count for Finland

    # Check if the station is from a participating country
    if any(prefix.startswith(country) for country in participating_countries):
        # Check if exchange was received correctly
        if self.contact.get("NR", "") and self.contact.get("Region", ""):
            return 2  # Correct QSO with complete exchange
        return 1  # QSO with wrong received message
    return 0  # Non-participating country

def show_mults(self):
    """Show multipliers"""
    result = self.database.fetch_mult_count(1)
    if result is not None:
        mults = int(result.get("count", 0))
        return mults
    return 0

def show_qso(self):
    """Show QSO points"""
    result = self.database.fetch_points()
    if result is not None:
        score = result.get("Points", "0")
        if score is None:
            score = "0"
        return int(score)
    return 0

def adif(self):
    """Generate ADIF record"""
    return gen_adif(self)

def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """Output line to cabrillo file"""
    file_descriptor.write(line_to_output + ending)

def cabrillo(self, file_encoding):
    """Generate Cabrillo file"""
    # Determine category based on power and operator type
    power = self.station.get('Power', 'HIGH')
    operator = self.station.get('Operator', 'SINGLE-OP')
    
    if operator == 'MULTI-OP':
        category = 'C'  # Multi Operator
    else:
        if power == 'LOW':  # 100W or less
            category = 'B'  # Single Operator LP
        else:
            category = 'A'  # Single Operator HP

    cabrillo_header = (
        f"START-OF-LOG: 3.0\n"
        f"CALLSIGN: {self.station.get('Call', '')}\n"
        f"CONTEST: {cabrillo_name}\n"
        f"CATEGORY: {category}\n"
        f"CATEGORY-ASSISTED: {self.station.get('Assisted', 'NON-ASSISTED')}\n"
        f"CATEGORY-BAND: ALL\n"
        f"CATEGORY-MODE: SSB\n"
        f"CATEGORY-OPERATOR: {operator}\n"
        f"CATEGORY-POWER: {power}\n"
        f"CATEGORY-STATION: FIXED\n"
        f"CATEGORY-TRANSMITTER: ONE\n"
        f"CLUB: {self.station.get('Club', '')}\n"
        f"CREATED-BY: Not1MM v{__version__}\n"
        f"NAME: {self.station.get('Name', '')}\n"
        f"ADDRESS: {self.station.get('Street1', '')}\n"
        f"ADDRESS: {self.station.get('Street2', '')}\n"
        f"ADDRESS: {self.station.get('City', '')}, {self.station.get('State', '')} {self.station.get('Zip', '')}\n"
        f"ADDRESS: {self.station.get('Country', '')}\n"
        f"OPERATORS: {self.station.get('Call', '')}\n"
        f"SOAPBOX: \n"
    )

    try:
        with open(
            Path(f"{self.station.get('Call', 'NOCALL')}_{cabrillo_name}.log"),
            "w",
            encoding=file_encoding,
        ) as file_descriptor:
            output_cabrillo_line(cabrillo_header, "", file_descriptor, file_encoding)
            result = self.database.get_all_contacts()
            for item in result:
                freq = str(item.get("Freq", "")).split(".")[0]
                if len(freq) > 4:
                    freq = freq[0:4]
                output_cabrillo_line(
                    (
                        f"QSO: {freq:>4} PH "
                        f"{datetime.datetime.strptime(item.get('Date', ''), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H%M')} "
                        f"{self.station.get('Call', ''):>13} "
                        f"{item.get('SNT', ''):>3} {item.get('SentNr', ''):>3} {self.station.get('Region', ''):>2} "
                        f"{item.get('Call', ''):>13} "
                        f"{item.get('RCV', ''):>3} {item.get('NR', ''):>3} {item.get('Region', ''):>2}"
                    ),
                    "\n",
                    file_descriptor,
                    file_encoding,
                )
            output_cabrillo_line("END-OF-LOG:", "\n", file_descriptor, file_encoding)
    except IOError as err:
        logger.warning("IO Error: %s", err)

def recalculate_mults(self):
    """Recalculate multipliers"""
    self.database.recalc_mults()

def process_esm(self, new_focused_widget=None, with_enter=False):
    """Process ESM"""
    if new_focused_widget:
        new_focused_widget.setFocus()
        if with_enter:
            self.process_enter()
        return

    if self.callsign.hasFocus():
        self.sent.setFocus()
        if with_enter:
            self.process_enter()
        return

    if self.sent.hasFocus():
        self.receive.setFocus()
        if with_enter:
            self.process_enter()
        return

    if self.receive.hasFocus():
        self.other_1.setFocus()
        if with_enter:
            self.process_enter()
        return

    if self.other_1.hasFocus():
        self.other_2.setFocus()
        if with_enter:
            self.process_enter()
        return

    if self.other_2.hasFocus():
        self.log_contact()
        self.callsign.setFocus()
        return

def get_mults(self):
    """Return multipliers"""
    result = self.database.fetch_mult_count(1)
    if result is not None:
        mults = int(result.get("count", 0))
        return mults
    return 0

def calc_score(self):
    """Return calculated score"""
    result = self.database.fetch_points()
    if result is not None:
        score = result.get("Points", "0")
        if score is None:
            score = "0"
        contest_points = int(score)
        result = self.database.fetch_mult_count(1)
        if result is not None:
            mults = int(result.get("count", 0))
            return contest_points * mults
    return 0

def just_points(self):
    """Get QSO points"""
    result = self.database.get_points()
    return result

def show_columns(self):
    """Return column names"""
    return [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq (KHz)",
        "Mode",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "Exchange1",
        "PTS",
    ] 