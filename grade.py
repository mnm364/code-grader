#!/usr/bin/env python3.5

import json, os, re, sys
from difflib import unified_diff
import subprocess
from subprocess import PIPE
from abc import ABCMeta, abstractmethod
from pathlib import Path
import glob


class ScoreBoard:
	def __init__(self, bound, strict=(True, True), name=''):
		self.bound = bound
		self.strict = strict
		self.score = 0
		self.explanation = ''
		self.name = name

	def adjust(self, value, reason='', comment=None):
		self.score += value
		if self.score < self.bound[0]:
			print('scoreboard: ' + self.name + ' underflow ' + str(self.bound[0]) + '#' + str(self.score) + '; reason: ' + reason)
			if self.strict[0]:
				self.score = max(self.score, self.bound[0])
		if self.score > self.bound[1]:
			print('scoreboard: ' + self.name + ' overflow ' + str(self.bound[0]) + '#' + str(self.score) + '; reason: ' + reason)
			if self.strict[1]:
				self.score = min(self.score, self.bound[1])
		self.explanation += '\n(' + '{:+.2f}'.format(value) + ') ' + reason
		if comment:
			self.explanation += '\ncomment: ' + comment

	def dump(self):
		return {
			'score': self.score,
			'output': self.name + '\n' + self.explanation
		}


class Student:
	def __init__(self, name='Mappy Redusir', max_score='0'):
		self.name = name
		self.score_board = ScoreBoard(max_score)


class Tester(metaclass=ABCMeta):
	def __init__(self, name='test--', max_score='0', note=''):
		self.name = name
		self.score = ScoreBoard((0, max_score))
		self.score.adjust(max_score, reason='Initializing at max pts.')
		self.note = note

	@abstractmethod
	def run(self): pass

	# TODO - make this cleaner for reuse!
	@staticmethod
	def find_files(filename, others=None):
		found = ''
		for f in glob.iglob('./**/' + filename, recursive=True):
			found = f
			break

		if len(found) > 0:
			found = found[2:]

		# crazy stuff to try to find it
		# if len(found) == 0 and others:
		# 	for other in others:
		# 		for f in glob.iglob('./**/' + other, recursive=True):
		# 			found = f
		# 			break

		return found

	@staticmethod
	def triple_sort(f):
		return sorted(f.splitlines(), key=lambda x: [int(i) for i in x.split()])


class StreamTester(Tester):

	LANGS = {
		'python':'py',
		'perl':'pl'
	}

	_FILES = {
		'mapper': 'fof.mapper',
		'reducer': 'fof.reducer'
	}

	def __init__(self, **kwargs):
		kwargs['name'] = 'stream tester'
		super().__init__(**kwargs)
		self.files = {}
		self.data = 'simple.input/*'
		self.output = 'Script stream tester'
		self.lang = ''
		self.extension = ''

	def run(self):

		# search for filename match w/in directory, and collect info
		for label, name in StreamTester._FILES.items():
			for lang, ext in StreamTester.LANGS.items():
				filename = Tester.find_files(name + '.' + ext)
				if filename.find('/') != -1:
					self.score.adjust(-0.5, reason='wrong filename or directory format [' + filename + ']')
				if Path(filename).is_file():
					self.files[label] = filename
					self.lang = lang + ' '
					break

		# run with shebang if present
		for fn in self.files.values():
			with open(fn, 'r') as f:
				if not re.search(r'#!', f.readline()):
					self.score.adjust(-0.5, reason='missing the shebang in ' + fn)
					continue

			self.lang = './'

			# set runnable permission
			subprocess.Popen(['chmod', '755', fn])

		mapper = self.lang + self.files.get('mapper', 'python mapper.py')
		reducer = self.lang + self.files.get('reducer', 'python reducer.py')
		cmd = 'cat ' + self.data + ' | ' + mapper + ' | sort | ' + reducer + ' | sort'
		print(cmd)
		try:
			student_solution = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
			cleaned = '\n'.join(map(lambda x: x.strip(), student_solution.replace('\t', ' ').splitlines()))

			if student_solution != cleaned:
				self.score.adjust(-1, reason='invalid output format for map/reduce')
				student_solution = cleaned

			try:
				with open('simple.out', 'r') as solution:
					diff = unified_diff(
						Tester.triple_sort(student_solution),
						Tester.triple_sort(solution.read()),
						tofile='solution'
					)

				diff = list(diff)
				if len(diff) != 0:
					self.score.adjust(-5, reason='Failed diff: ' + '\n'.join(line for line in diff))

			except IOError:
				sys.stderr.write('GRADER ERROR: make sure bucket6 is in grading directory!\n')
			except ValueError:
				self.score.adjust(-5, reason='output format may be wrong (consider submitting regrade request!).\nYour solution:\n' + student_solution)
			except:
				self.score.adjust(-5, reason='unknown but fatal failure (consider submitting regrade request!).\n' + str(sys.exc_info()[0]) + '\n' + student_solution)
		except subprocess.CalledProcessError as e:
			self.score.adjust(-3, reason='issue with command (consider regrade request!):\n' + str(e.output) + '\n' + cmd)

		return {
			'score': self.score.score,
			'max_score': self.score.bound[1],
			'output': self.output + '\n' + self.score.explanation
		}


class BucketTest(Tester):
	def __init__(self, **kwargs):
		kwargs['name'] = 'bucket tester'
		super().__init__(**kwargs)
		self.output = 'Bucket Tester'

	def run(self):

		url = ''
		bucket = Tester.find_files('bucket.txt')

		# enforce good format
		if bucket != 'bucket.txt':
			self.score.adjust(-0.5, reason='bad bucket.txt format [' + bucket + ']')

		try:
			with open(bucket) as f:
				url = re.search(r'(https://\S*[fF]o[fF]\.output)', f.read()).group(1) + '/'
				if url is None:
					print('GSUTIL USED')
					url = re.search(r'(gs://\S*[fF]o[fF]\.output)/part?', f.read()).group(1) + '/'
					self.score.adjust(0, reason='workaround for gsutil in grading script, it works. Awesome job!')
				if url is not None:
					self.score.adjust(0, reason='valid url in bucket.txt file')
		except:
			self.score.adjust(-5, reason='no bucket.txt file!')

		try:
			ext = 'part-r-00006' # part-00006
			cmd = ' '.join(['curl -s -S', url + ext])
			student_solution = subprocess.check_output(cmd, shell=True).decode('utf-8')

			# throw error on invalid url extension (part-r-00006 or part-00006)
			try:
				firstline = student_solution.splitlines()[0]
				dummy = [int(x) for x in firstline.split()]
			except ValueError:
				ext = 'part-00006' # part-00006
				cmd = ' '.join(['curl -s -S', url + ext])
				student_solution = subprocess.check_output(cmd, shell=True).decode('utf-8')

			print('\n' + cmd)

			# print(student_solution)

			# check for valid bucket
			if len(student_solution) > 0:
				self.score.adjust(0, reason='valid bucket in bucket file')

			try:
				with open('bucket6', 'r') as solution:
					diff = unified_diff(
						Tester.triple_sort(student_solution),
						Tester.triple_sort(solution.read()),
						tofile='solution',
						fromfile='student output'
					)
				diffstr = ''
				correct = True
				for line, i in zip(diff, range(20)):
					correct = False
					diffstr += '\n' + line
				for line in diff:
					correct = False
					break
				if correct:
					print('Integer ordered')

				if not correct:
					with open('bucket6_lex', 'r') as solution:
						diff = unified_diff(
							Tester.triple_sort(student_solution),
							Tester.triple_sort(solution.read()),
							tofile='solution',
							fromfile='student output'
						)
					diffstr = ''
					correct = True
					for line, i in zip(diff, range(20)):
						correct = False
						diffstr += '\n' + line
					for line in diff:
						correct = False
						break
					if correct:
						print('Lexographically ordered')

				if not correct:
					self.score.adjust(-5, reason='failed diff for gcloud hadoop output (' + ext + ') - showing only first 20 diffs:' + diffstr)

			except IOError:
				sys.stderr.write('GRADER ERROR: make sure bucket6 and bucket6_lex files are in grading directory!\n')
			except ValueError as e:
				self.score.adjust(-0.5, reason='output format may be wrong (consider submitting regrade request!)' + '\n ' + str(e))

		except subprocess.CalledProcessError as e:
			self.score.adjust(-5, reason='issue with curl command, did you make your bucket public? (consider regrade request!):\n' + cmd + '\n ' + str(e.output))
		except:
			self.score.adjust(0, reason='unknown failure')

		return {
			'score': self.score.score,
			'max_score': self.score.bound[1],
			'output': self.output + '\n' + self.score.explanation
		}


# TODO
class DirectoryTester(Tester):
	def __init__(self, **kwargs):
		super().__init__(kwargs)

	def run(self): pass


def main():
	tests = [
		StreamTester(max_score=10.0),
		BucketTest(max_score=15.0)
	]

	res = {
		'output':'this tests your code',
		'tests': [test.run() for test in tests]
	}

	print(json.dumps(res, indent=4, separators=(',', ': ')))

	with open('out.json', 'w') as jout:
		jout.write(json.dumps(res))

if __name__ == '__main__':
	main()
