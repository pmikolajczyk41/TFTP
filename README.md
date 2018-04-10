# TFTP
Trivial File Transfer Protocol implemented in Python

### Goal
The primary goal of this project for Computer Networks course was to implement main ideas of TFTP following the RFCs:
  - RFC 1350
  - RFC 2347
  - RFC 2348
  - RFC 7440
  
  
### Features and limitations
Functionality is limited to the one scenario, in which the client reads the file from the server. A reason for this was that the opposite communication would look exaclty the same (with very subtle differences in the beginning negotiations).

Logging is switched on by default. To disable it, one should comment line: `logging.basicConfig(level=logging.DEBUG)`

While starting server, port and path to files being served can be given as arguments. Default port is set in 'common.py', default path is the current one.

Each connection is handled in a new thread.

While starting client, arguments given describes target server and target file. Inside code, one can change windowsize. Read file can be either written to a stdout or hashed by MD5 (then hash is written).

In 'common.py' timeout policy can be configured.
