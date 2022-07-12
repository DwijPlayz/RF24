/*
 Copyright (C) 2011 J. Coliz <maniacbug@ymail.com>

 This program is free software; you can redistribute it and/or
 modify it under the terms of the GNU General Public License
 version 2 as published by the Free Software Foundation.


 03/17/2013 : Charles-Henri Hallard (http://hallard.me)
              Modified to use with Arduipi board http://hallard.me/arduipi
						  Changed to use modified bcm2835 and RF24 library

 */

/**
 * Channel scanner
 *
 * Example to detect interference on the various channels available.
 * This is a good diagnostic tool to check whether you're picking a
 * good channel for your application.
 *
 * Inspired by cpixip.
 * See http://arduino.cc/forum/index.php/topic,54795.0.html
 */

/*
 * How to read the output:
 * - The header is a list of supported channels in decimal written vertically.
 * - Each column corresponding to the vertical header is a hexadecimal count of
 *   detected signals (max is 15 or 'f').
 *
 * The following example
 *    000
 *    111
 *    789
 *    ~~~   <- just a divider between the channel's vertical labels and signal counts
 *    1-2
 * can be interpreted as
 * - 1 signal detected on channel 17
 * - 0 signals (denoted as '-') detected on channel 18
 * - 2 signals detected on channel 19
 *
 * Each line of signal counts represent 100 passes of the supported spectrum.
 */
#include <string>   // string, getline()
#include <iostream> // cout, endl, flush, cin
#include <RF24/RF24.h>

using namespace std;

/****************** Linux ***********************/
// Radio CE Pin, CSN Pin, SPI Speed
// CE Pin uses GPIO number with BCM and SPIDEV drivers, other platforms use their own pin numbering
// CS Pin addresses the SPI bus number at /dev/spidev<a>.<b>
// ie: RF24 radio(<ce_pin>, <a>*10+<b>); spidev1.0 is 10, spidev1.1 is 11 etc..

// Generic:
RF24 radio(22, 0);
/****************** Linux (BBB,x86,etc) ***********************/
// See http://nRF24.github.io/RF24/pages.html for more information on usage
// See http://iotdk.intel.com/docs/master/mraa/ for more information on MRAA
// See https://www.kernel.org/doc/Documentation/spi/spidev for more information on SPIDEV

// Channel info
const uint8_t num_channels = 126; // 0-125 are supported
uint8_t values[num_channels];     // the array to store summary of signal counts per channel

// To detect noise, we'll use the worst addresses possible (a reverse engineering tactic).
// These addresses are designed to confuse the radio into thinking
// that the RF signal's preamble is part of the packet/payload.
const uint8_t noiseAddress[][2] = {{0, 0x55}, {0, 0xAA}};

const int num_reps = 100; // number of passes for each scan of the entire spectrum

void printHeader()
{
    // print the hundreds digits
    for (int i = 0; i < num_channels; ++i)
        cout << (i / 100);
    cout << endl;

    // print the tens digits
    for (int i = 0; i < num_channels; ++i)
        cout << ((i % 100) / 10);
    cout << endl;

    // print the singles digits
    for (int i = 0; i < num_channels; ++i)
        cout << (i % 10);
    cout << endl;

    // print the header's divider
    for (int i = 0; i < num_channels; ++i)
        cout << '~';
    cout << endl;
}

int main(int argc, char** argv)
{
    // print example's name
    cout << argv[0] << endl;

    // Setup the radio
    if (!radio.begin()) {
        cout << "Radio hardware not responding!" << endl;
        return 1;
    }

    // set the data rate
    cout << "Select your Data Rate. ";
    cout << "Enter '1' for 1Mbps, '2' for 2Mbps, '3' for 250kbps. Defaults to 1Mbps." << endl;
    string dataRate = "";
    getline(cin, dataRate);
    if (dataRate.length() >= 1 && static_cast<char>(dataRate[0]) == '2') {
        cout << "Using 2 Mbps." << endl;
        radio.setDataRate(RF24_2MBPS);
    }
    else if (dataRate.length() >= 1 && static_cast<char>(dataRate[0]) == '3') {
        cout << "Using 250 kbps." << endl;
        radio.setDataRate(RF24_250KBPS);
    }
    else {
        cout << "Using 1 Mbps." << endl;
        radio.setDataRate(RF24_1MBPS);
    }

    // configure the radio
    radio.setAutoAck(false);  // Don't acknowledge arbitrary signals
    radio.disableCRC();       // Accept any signal we find
    radio.setAddressWidth(2); // A reverse engineering tactic (not typically recommended)
    radio.openReadingPipe(0, noiseAddress[0]);
    radio.openReadingPipe(1, noiseAddress[1]);

    // Get into standby mode
    radio.startListening();
    radio.stopListening();
    radio.flush_rx();

    radio.printPrettyDetails();

    // print the vertical header
    printHeader();

    // forever loop
    while (1) {
        // Clear measurement values
        memset(values, 0, sizeof(values));

        // Scan all channels num_reps times
        int rep_counter = num_reps;
        while (rep_counter--) {

            for (int i = 0; i < num_channels; ++i) {

                // Select this channel
                radio.setChannel(i);

                // Listen for a little
                radio.startListening();
                delayMicroseconds(130);
                // for some reason, this flag is more accurate on Linux when still in RX mode.
                bool foundSignal = radio.testRPD();
                radio.stopListening();

                // Did we get a signal?
                if (foundSignal || radio.testRPD()) {
                    ++values[i];
                    radio.flush_rx(); // discard packets of noise
                }

                // output the summary/snapshot for this channel
                if (values[i]) {
                    // Print out channel measurements, clamped to a single hex digit
                    cout << hex << min(0xF, static_cast<int>(values[i])) << flush;
                }
                else {
                    cout << '-' << flush;
                }
            }
            cout << '\r' << flush;
        }
        cout << endl;
    }

    return 0;
}

// vim:ai:cin:sts=2 sw=2 ft=cpp
