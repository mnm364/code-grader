import json, os, re, sys
from difflib import unified_diff
import subprocess
from subprocess import PIPE
from abc import ABCMeta, abstractmethod
from pathlib import Path
import glob

class ScoreBoard:
	def __init__(self, bounds, strict=(True, True)):
		self.min_score = bounds(0)
		self.max_score = bounds(1)
		self.bounds = bounds
		self.strict = strict
		self.score = 0

	def adjust(self, value, reason='', comment=''):
		self.score += value

class Student:

	def __init__(self, name='Mappy Redusir', max_score='0'):
		self.name = name
		self.score_board = ScoreBoard(max_score)



class Tester(metaclass=ABCMeta):

	def __init__(self, name='test?', max_score='0', note=''):
		self.name = name
		self.score = 0
		self.max_score = max_score
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
		bad = 1 if found != filename else 0

		# crazy stuff to try to find it
		if len(found) == 0 and others:
			for other in others:
				for f in glob.iglob('./**/' + other, recursive=True):
					found = f
					break

		return found, bad

# TODO
class DirectoryTester(Tester):
	def __init__(self, **kwargs):
		super().__init__(kwargs)

	def run(self): pass

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
		self.score = 0
		self.output = 'Script stream tester'
		self.badformat = 0

	def run(self):

		# TODO - check if langs and exts match

		self.lang = ''
		self.extension = ''

		# search for filename match w/in directory, and collect info
		for label, name in StreamTester._FILES.items():
			for lang, ext in StreamTester.LANGS.items():
				filename = name + '.' + ext
				filename, bad = Tester.find_files(filename)
				if Path(filename).is_file():
					self.badformat += 1.5*bad
					self.files[label] = filename
					self.lang = lang + ' '
					break

		use_shebang = True
		# verify that shebang is present
		for fn in self.files.values():
			with open(fn, 'r') as f:
				if not re.search(r'#!', f.readline()):
					use_shebang = False
					continue

			self.lang = './'

			# set runnable permission
			subprocess.Popen(['chmod', '755', fn])

		# DEBUG
		print(self.lang)
		print(self.files)
		# END DEBUG

		mapper = self.lang + self.files['mapper']
		reducer = self.lang + self.files['reducer']
		cmd = 'cat ' + self.data + ' | ' + mapper + ' | sort | ' + reducer + ' | sort' #  > ./student.simple.out
		print(cmd)
		student_solution = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
		cleaned = '\n'.join(map(lambda x: x.strip(), student_solution.replace('\t', ' ').splitlines()))

		if student_solution != cleaned:
			self.score -= 2
			self.output += '\n(-2) invalid output format for map/reduce (eeek this might screw up the big boy test...)'
			student_solution = cleaned

		triple_sort = lambda f: sorted(f.splitlines(), key=lambda x: [int(i) for i in x.split()])

		# with open('student.simple.out', 'r') as output:
		with open('simple.out', 'r') as solution:
			diff = unified_diff(
				triple_sort(student_solution),
				triple_sort(solution.read()),
				tofile='solution'
			)

		diff = list(diff)
		if len(diff) == 0:
			self.score += 10

		self.output += '\nDiff:\n'
		for line in diff:
			self.output += line + '\n'

		self.score -= self.badformat
		self.output += '\nformat: -' + str(self.badformat)

		if not use_shebang:
			self.score -= 2
			self.output += '\nYo missing the SHEBANG!!!'

		return {
			'score': self.score,
			'max_score': self.max_score,
			'output': self.output
		}

class BucketTest(Tester):
	def __init__(self, **kwargs):
		kwargs['name'] = 'bucket tester'
		super().__init__(**kwargs)
		self.score = 0
		self.output = 'Bucket Tester'
		self.badformat = 0

	def run(self):

		url = ''
		bucket, stat = Tester.find_files('bucket.txt')
		try:
			with open(bucket) as f:
				url = re.search(r'(https://\S*fof\.output)', f.read()).group(1) + '/'
		except:
			self.output += '\nno bucket.txt file'
			self.badformat += 10

		ext = 'part-r-00006'
		cmd = ' '.join(['curl', url + ext])
		print(cmd)
		student_solution = subprocess.check_output(cmd, shell=True).decode('utf-8')

		# check for valid bucket
		if len(student_solution) > 10:
			self.score += 15

		# enforce good format
		if bucket == 'bucket.txt':
			self.score += 2
			self.output += '\ngood: bucket.txt format good'

		self.score = max(self.score - self.badformat, 0)

		triple_sort = lambda f: sorted(f.splitlines(), key=lambda x: [int(i) for i in x.split()])

		try:
			with open('bucket6', 'r') as solution:
				diff = unified_diff(
					triple_sort(student_solution),
					triple_sort(solution.read()),
					tofile='solution'
				)

				correct = True
				for line in zip(diff, range(20)):
					correct = False
					self.output += '\n' + line
				for line in diff:
					correct = False

				if not correct:
					self.output += '\nincorrect output for large file diff! \
						\nnote: diff only shows for first 20 lines of diff'
					self.score -= 5

		except IOError:
			sys.stderr.write('GRADER ERROR: make sure bucket6 is in grading directory!\n')

		return {
			'score': self.score,
			'max_score': self.max_score,
			'output': self.output
		}

def main():
	tests = [
		StreamTester(max_score=10.0),
		BucketTest(max_score=15.0)
	]

	res = {
		'output':'this tests your code',
		'tests': [test.run() for test in tests]
	}

	print (res)

	with open('out.json', 'w') as jout:
		jout.write(json.dumps(res))

if __name__ == '__main__':
	main()
