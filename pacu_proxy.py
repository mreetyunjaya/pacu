class PacuProxy(object):

    def __init__(self):
        self.host = '0.0.0.0'
        self.port = 80
        self.socket = None
        self.all_connections = []
        self.all_addresses = []

    def prepare_server(self, global_config):
        self.host = global_config['ProxyIP']
        self.port = global_config['ProxyPort']
        signal.signal(signal.SIGTERM, self.quit_gracefully)
        return

    # Close the listener
    def quit_gracefully(self, signal=None, frame=None):
        print('\n** Stopping proxy listener... **')
        for conn in self.all_connections:
            try:
                conn.shutdown(2)
                conn.close()
            except Exception as e:
                print('** Could not close connection {} **'.format(str(e)))
        self.socket.close()
        print('\n** Proxy listener stopped. **')

    # Create the initial socket
    def socket_create(self):
        try:
            self.socket = socket.socket()
        except socket.error as msg:
            print('** Socket creation error: {} **'.format(str(msg)))
            return
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return

    # Bind socket to specified port and listen for new agents
    def socket_bind(self):
        try:
            self.socket.bind((self.host, int(self.port)))
            self.socket.listen(5)
        except socket.error as e:
            print('** Socket binding error: {} **'.format(str(e)))
            time.sleep(5)
            self.socket_bind()
        return

    # Accept new agents
    def accept_connections(self):
        for c in self.all_connections:
            c.close()
        self.all_connections = []
        self.all_addresses = []
        while 1:
            try:
                conn, address = self.socket.accept()
                conn.setblocking(1)
                client_hostname = conn.recv(1024).decode('utf-8')
                address = address + (client_hostname,)
            except Exception as e:
                if 'not a socket' in str(e):
                    break
                print('** Error accepting connections: {} **'.format(str(e)))
                continue
            self.all_connections.append(conn)
            self.all_addresses.append(address)
            print('\n** Connection has been established: {} ({}) **'.format(address[-1], address[0]))
        return

    # Run a shell command on an agent
    def run_cmd(self, target, conn, cmd):
        conn.send(str.encode(' '))
        cwd_bytes = self.read_command_output(conn)
        try:
            if len(str.encode(cmd)) > 0:
                conn.send(str.encode(cmd))
                cmd_output = self.read_command_output(conn)
                client_response = str(cmd_output, 'utf-8')
                print(client_response, end='')
        except Exception as e:
            print('** Connection was lost {} **'.format(str(e)))
            del self.all_connections[target]
            del self.all_addresses[target]
        return

    # Kill an agent
    def quit(self, target, conn):
        conn.send(str.encode(' '))
        cwd_bytes = self.read_command_output(conn)
        try:
            cmd = 'q'
            if len(str.encode(cmd)) > 0:
                conn.sendall(str.encode(cmd))
                cmd_output = self.read_command_output(conn)
                client_response = str(cmd_output, 'utf-8')
                print(client_response, end='')
        except:
            pass
        del self.all_connections[target]
        del self.all_addresses[target]
        return

    # Lists all PacuProxy agents
    def list_connections(self):
        results = ''
        for i, conn in enumerate(self.all_connections):
            try:
                conn.send(str.encode(' '))
                conn.recv(20480)
            except:
                del self.all_connections[i]
                del self.all_addresses[i]
                continue
            results += '{}   | {}   | {}   | {}\n'.format(str(i), str(self.all_addresses[i][0]), str(
                self.all_addresses[i][1]), str(self.all_addresses[i][2]))
        print('----- Clients -----\nAgent ID | IP   | Process ID | Hostname\n{}'.format(results))
        return

    # Select the target agent
    def get_target(self, cmd):
        target = cmd.split(' ')[-1]
        try:
            target = int(target)
        except:
            print('** Client index should be an integer. **')
            return None, None
        try:
            conn = self.all_connections[target]
        except IndexError:
            print('** Not a valid selection. **')
            return None, None
        print('\n** You are now connected to {} **'.format(str(self.all_addresses[target][2])))
        return target, conn

    # Read command output
    def read_command_output(self, conn):
        raw_msglen = self.recvall(conn, 4)
        if not raw_msglen:
            return None
        msglen = struct.unpack('>I', raw_msglen)[0]
        # Read the message data
        return self.recvall(conn, msglen)

    # Receive n bytes helper function
    def recvall(self, conn, n):
        data = b''
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data
