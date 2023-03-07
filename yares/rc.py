"""
	Yares Compiler
"""
import os
import sys
import base64
import gzip
import bson
import json
import yaml
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import TerminalFormatter
import ipaddress 
import logging
logger = logging.getLogger(__name__)
from .query import Q


class BadIPAddress(Exception):
	pass


class RC:

	FN_DEFAULT = '_default.yaml'
	TAG_HIDDEN = '__'
	
	def __init__(self, base_name, env={}, debug=False):
		self.base_name = base_name
		self.debug = debug
		self.env = env
		self.body = {}
		self.preload = False
		self.preload_data = {}

	def atomize(self, value):
		try:
			try:
				return int(value.value)
			except:
				return float(value.value)
		except:
			return value.value

	def prepare_var_value(self, value):
		if isinstance(value, yaml.nodes.ScalarNode):
			return self.atomize(value)

		if isinstance(value, yaml.nodes.SequenceNode):
			done = []
			for x in value.value:
				done.append(self.atomize(x))
			return done

	def parse_ip_addr(self, address):
		try:
			ip = ipaddress.ip_address(address)
		except ValueError:
			raise BadIPAddress()
		return list(ip.packed)

	def compile(self, target='json', compress=True):
		self.preload = True
		self.proc(target=target, compress=compress)
		self.preload = False
		return self.proc(target=target, compress=compress)

	def proc(self, target='json', compress=True):

		class QueryTag(yaml.YAMLObject):
			@classmethod
			def from_yaml(cls, loader, node):
				if not self.preload:
					return Q(self.preload_data, node.value)

		class LoadTextTag(yaml.YAMLObject):
			@classmethod
			def from_yaml(cls, loader, node):
				return self.load_text(node.value)

		class LoadBinaryTag(yaml.YAMLObject):
			@classmethod
			def from_yaml(cls, loader, node):
				return self.load_bin(node.value)

		class LoadBase64Tag(yaml.YAMLObject):
			@classmethod
			def from_yaml(cls, loader, node):
				return self.load_b64(node.value)

		class EvalTag(yaml.YAMLObject):
			@classmethod
			def from_yaml(cls, loader, node):
				return self.pyeval(node.value)

		class SourceYAMLTag(yaml.YAMLObject):
			@classmethod
			def from_yaml(cls, loader, node):
				return self.load_yaml(str(node.value))

		class SourceBSONTag(yaml.YAMLObject):
			@classmethod
			def from_yaml(cls, loader, node):
				return self.load_bson(str(node.value))

		"""
		class DefineTag(yaml.YAMLObject):
			@classmethod
			def from_yaml(cls, loader, node):
				name, value = loader.construct_sequence(node)
				self.env[name] = value
				return value
		"""

		class ParseIPTag(yaml.YAMLObject):
			@classmethod
			def from_yaml(cls, loader, node):
				return self.parse_ip_addr(node.value)

		yaml.SafeLoader.add_constructor('!load-text', LoadTextTag.from_yaml)
		yaml.SafeLoader.add_constructor('!load-binary', LoadBinaryTag.from_yaml)
		yaml.SafeLoader.add_constructor('!load-base64', LoadBase64Tag.from_yaml)
		
		yaml.SafeLoader.add_constructor('!source', SourceYAMLTag.from_yaml)
		yaml.SafeLoader.add_constructor('!source-bson', SourceBSONTag.from_yaml)
		
		yaml.SafeLoader.add_constructor('!eval', EvalTag.from_yaml)
		yaml.SafeLoader.add_constructor('!query', QueryTag.from_yaml)
		yaml.SafeLoader.add_constructor('!parse-ip', ParseIPTag.from_yaml)
		#yaml.SafeLoader.add_constructor('!define', DefineTag.from_yaml)

		outfilename = self.base_name + '.' + target
		done = self.load_yaml(self.FN_DEFAULT)
		self.body = done
		if not done:
			raise Exception('Nothing to do!')
		if not isinstance(done, dict):
			raise Exception('Dictionary object expected!')

		# remove hidden keys
		done_opt = {}
		for y in done.keys():
			if y[:2] != self.TAG_HIDDEN:
				done_opt[y] = done[y]
		done = done_opt

		# pre-processing
		# TODO: FIXME: Very ugly sol.
		if self.preload:
			c_base_name = "yares_" + self.base_name.replace("/", "_")
			fh=open("/tmp/%s" % c_base_name, "w")
			fh.write(json.dumps(done))
			fh.close()
			
			fh=open("/tmp/%s" % c_base_name, "r")
			self.preload_data=json.loads(fh.read())
			fh.close()
			# unlink file?

		if not self.preload:
			if self.debug:
				self.print_debug(done)

			if target == 'json':
				dump = json.dumps(done)
				ft = 'w'

			if target == 'bson':
				dump = bson.dumps(done)
				ft = 'wb'

			if compress:
				outfilename += '.gz'
				fh = gzip.open(outfilename, 'wb')
				if isinstance(dump, str):
					dump = bytes(dump, 'ascii')
			else:
				fh = open(outfilename, ft)
			fh.write(dump)
			fh.close()
			logger.info("Sucessfull! (%s Bytes)", len(dump))
		return 0

	def print_debug(self, obj):
		json_str = json.dumps(obj, indent=4, sort_keys=True)
		print(highlight(json_str, JsonLexer(), TerminalFormatter()))

	def load_yaml(self, filename):
		if self.preload:
			logger.debug("Processing file... %s", filename)
		else:
			logger.debug("Adding source...   %s", filename)
		fn = self.base_name + os.path.sep + filename
		fh = open(fn, 'r')
		obj = yaml.safe_load(fh)
		fh.close()
		return obj

	def load_bson(self, filename):
		if self.preload:
			logger.debug("Processing file... %s", filename)
		else:
			logger.debug("Adding source...   %s", filename)
		fn = self.base_name + os.path.sep + filename
		fh = open(fn, 'rb')
		data = fh.read()
		obj = bson.loads(data)
		fh.close()
		return obj

	def load_text(self, filename):
		logger.debug("Loading file...    %s", filename)
		fn = self.base_name + os.path.sep + filename
		fh = open(fn, 'r')
		data = fh.read()
		fh.close()
		return data

	def load_b64(self, filename):
		logger.debug("Loading file...    %s", filename)
		fn = self.base_name + os.path.sep + filename
		fh = open(fn, 'rb')
		data = fh.read()
		fh.close()
		return base64.b64encode(data).decode('ascii')

	def load_bin(self, filename):
		logger.debug("Loading file...    %s", filename)
		fn = self.base_name + os.path.sep + filename
		fh = open(fn, 'rb')
		data = fh.read()
		fh.close()
		return list(data)

	def pyeval(self, expression):
		if self.preload:
			self.env["Query"] = lambda q: 0
		else:
			self.env["Query"] = lambda q: Q(self.preload_data, q)
		return eval(expression, self.env)


def run_rc(base_name, env, compress=False, debug=False, to='bson'):
	logger.info("Compiling source base: %s", base_name)
	rc = RC(base_name, env=env, debug=debug)
	return rc.compile(target=to, compress=compress)
