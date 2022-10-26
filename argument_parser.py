import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(description='PyDrop v1.0')
    parser.add_argument('-s',
                        '--scan',
                        help='Scan for devices.',
                        type=int,
                        metavar='TIMEOUT',
                        nargs='?'
                        )

    parser.add_argument('-c',
                        '--connect',
                        help='Connect to devices. \
                        Supply a bluetooth address if known.',
                        action='store_true'
                        )

    parser.add_argument('-d',
                        '--disconnect',
                        help='Disconnect from a device. \
                        Supply a bluetooth address if known.',
                        action='store_true'
                        )

    parser.add_argument('-l',
                        '--list',
                        help='List known devices.',
                        action='store_true'
                        )

    parser.add_argument('-p',
                        '--pair',
                        help='Pair to a device.',
                        action='store_true'
                        )

    parser.add_argument('-a',
                        '--advertise',
                        help='Advertise OBEX protocol.',
                        action='store_true'
                        )

    args_parsed = parser.parse_args()
    return args_parsed


if __name__ == '__main__':
    print("This file should not be run alone.")