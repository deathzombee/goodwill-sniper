import argparse
import subprocess
import sys
import psutil
from dateutil.parser import parse
import utils

# init database
conn, c = utils.get_conn()
c.execute("SELECT * FROM sqlite_master WHERE type = 'table' AND (name = 'listings' OR name = 'process')")
tables = c.fetchall()
if len(tables) != 2:
    print('initializing database')
    with open('init_database.sql', 'r') as init_script:
        sql = init_script.read()
    c.executescript(sql)
    conn.commit()
c.close()
conn.close()


# New better cli interface
def start():
    dconn, cmd = utils.get_conn()

    cmd.execute('SELECT pid FROM process')
    pid_row = cmd.fetchone()

    if pid_row is not None and psutil.pid_exists(pid_row['pid']):
        print('Sniper process is already running')
        return
    else:
        cmd.execute('DELETE FROM process')
        dconn.commit()

        proc = subprocess.Popen(['python', 'daemon.py'], start_new_session=True)
        pid = proc.pid

        cmd.execute('INSERT INTO process(pid) VALUES(?)', (pid,))
        dconn.commit()

        print('Sniper process succcessfully started with PID ' + str(pid))

    cmd.close()
    dconn.close()


def stop():
    dconn, cmd = utils.get_conn()

    cmd.execute('SELECT * FROM process')
    pid_row = cmd.fetchone()
    if pid_row is not None and psutil.pid_exists(pid_row['pid']):
        psutil.Process(pid_row['pid']).kill()
        print('Sniper process successfully terminated')
    else:
        print('Sniper process is not currently running')

    cmd.execute('DELETE FROM process')
    dconn.commit()

    cmd.close()
    dconn.close()


def restart():
    stop()
    start()


def status():
    dconn, cmd = utils.get_conn()

    cmd.execute('SELECT pid FROM process')
    pid_row = cmd.fetchone()

    if pid_row is not None and psutil.pid_exists(pid_row['pid']):
        print('Sniper process is running')
    else:
        print('Sniper process is *not* running')

    cmd.close()
    dconn.close()


def create():
    parser = argparse.ArgumentParser(description='Create new item to snipe')
    required = parser.add_argument_group('required named arguments')
    required.add_argument('-i', '--item', action='store', type=int, required=True)
    required.add_argument('-m', '--max', action='store', type=int, required=True)
    args = parser.parse_args(sys.argv[2:])

    item_data = utils.retreive_listing_information(args.item)

    dconn, cmd = utils.get_conn()
    cmd.execute('INSERT INTO listings(item_id, max_bid, name, ending_dt) VALUES(?,?,?,?)',
                (args.item, args.max, item_data['name'], item_data['ending_dt']))
    dconn.commit()

    print('Successfully added snipe for item #' + str(args.item))

    cmd.close()
    dconn.close()


def delete():
    parser = argparse.ArgumentParser(description='Delete an item from sniping list')
    required = parser.add_argument_group('required named arguments')
    required.add_argument('-i', '--item', nargs='+', action='store', type=int, required=True)
    args = parser.parse_args(sys.argv[2:])

    dconn, cmd = utils.get_conn()
    for item in args.item:
        cmd.execute('DELETE FROM listings WHERE item_id=?', (item,))
    dconn.commit()
    cmd.close()
    dconn.close()

    try:
        utils.send_msg('update')
    except ConnectionRefusedError:
        pass


def update():
    parser = argparse.ArgumentParser(description='Delete an item from sniping list')
    required = parser.add_argument_group('required named arguments')
    required.add_argument('-i', '--item', action='store', type=int, required=True)
    required.add_argument('-m', '--max', action='store', type=int, required=True)
    args = parser.parse_args(sys.argv[2:])

    dconn, cmd = utils.get_conn()
    cmd.execute('UPDATE listings SET max_bid=? WHERE item_id=?', (args.max, args.item))
    dconn.commit()
    cmd.close()
    dconn.close()

    try:
        utils.send_msg('update')
    except ConnectionRefusedError:
        pass


def item_list():
    dconn, cmd = utils.get_conn()

    cmd.execute('SELECT * FROM listings ORDER BY ending_dt')
    listings = cmd.fetchall()
    for listing in listings:
        ending_dt = parse(listing['ending_dt'])
        print(
            str(listing['item_id']) + ' | ' + str(ending_dt) + ' | ' + str(listing['name']) + ' | Max Bid: ' + str(
                listing['max_bid']) + ' | URL: ' + 'https://www.shopgoodwill.com/Item/' + str(listing['item_id']))

    cmd.close()
    dconn.close()

    try:
        utils.send_msg('update')
    except ConnectionRefusedError:
        pass


def dump():
    utils.send_msg('dump')


def main():
    parser = argparse.ArgumentParser(
        description='Command Line Sniper for the Goodwill Shopping Website',
        usage='''sniper.py <command> [<args>]

List of sniper commands:
    start   Initializes the sniping background process
    stop    Terminates the sniping background process
    restart Terminates then initialized the sniping background process
    status  Prints the status of the sniping background process
    create  Adds and schedules a specified item to be sniped
    delete  Stops a specified item from being sniped
    update  Used to update the max bid for a specified item
    list    Prints the list of items scheduled to be sniped
'''
    )
    parser.add_argument('command', help='name of command to be executed')

    args = parser.parse_args(sys.argv[1:2])
    command_mapping = {
        'start': start,
        'stop': stop,
        'restart': restart,
        'status': status,
        'create': create,
        'delete': delete,
        'update': update,
        'list': item_list,
        'dump': dump,
    }
    command = command_mapping.get(args.command)
    if command is None:
        print('Unrecognized command')
        parser.print_help()
        exit(1)
    command()


if __name__ == '__main__':
    main()
