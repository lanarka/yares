"""
	Yares Test
"""
import traceback
import coloredlogs
import sys
import logging
logger = logging.getLogger(__name__)

from yares import run_rc #.

# FIXME: Add to args
# options
debug = True
compress = False
output_format = 'bson'
environment = {

		# initial values
		'hello': 'Hello',
		'world': -100,

		# custom function
		'string_reverse_func': lambda x: x[::-1] 

	}

def on_unhandled_exception(type, value, tb):
	tb_info = "".join(traceback.format_exception(type, value, tb))
	msg = "%s: %s" % (type.__name__, tb_info)
	logger.critical(msg)

def main():
	if not len(sys.argv) == 2: 
		print('Usage: %s <base-name>' % sys.argv[0])
		sys.exit(1)
	base_name = sys.argv[1]

	logger = logging.getLogger("main")
	coloredlogs.DEFAULT_DATE_FORMAT = "%d/%m/%y %H:%M:%S"
	coloredlogs.DEFAULT_FIELD_STYLES = {
		"asctime": {"color": "green"},
		"hostname": {"color": "white", "faint": True},
		"levelname": {"color": "cyan"},
		"name": {"color": "magenta"},
		"programname": {"color": "cyan"},
		"username": {"color": "yellow"}
	}
	coloredlogs.DEFAULT_LEVEL_STYLES = {
		"critical": {"color": "red"},
		"debug": {"color": "green"},
		"error": {"color": "red"},
		"info": {"color": "white"},
		"notice": {"color": "magenta"},
		"spam": {"color": "red", "faint": True},
		"success": {"color": "green", "faint": True},
		"verbose": {"color": "blue"},
		"warning": {"color": "yellow"}
	}
	sys.excepthook = on_unhandled_exception
	if debug:
		coloredlogs.install(level="DEBUG")
	done = run_rc(base_name, environment, to=output_format, debug=debug, compress=compress)
	sys.exit(done)
	
if __name__ == '__main__':
	main()
