# Copyright cefyr 2011-2013

# This file is part of Kalpana.

# Kalpana is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Kalpana is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Kalpana. If not, see <http://www.gnu.org/licenses/>.


import datetime, os, os.path, re 
import pluginlib, common
from math import ceil
from PyQt4 import QtGui
from PyQt4.QtCore import Qt


class UserPlugin(pluginlib.GUIPlugin):
    def start(self):
        self.nanowidget = NaNoSidebar(self.path, self.get_filepath, self.get_text)
        self.add_widget(self.nanowidget, pluginlib.EAST) 
        self.hotkeys = {'Ctrl+P': self.nanowidget.toggle_sidebar}
        self.commands = {'nn': (self.nanowidget.activate, 
                                'Start NaNo mode at [day]')}

    def file_saved(self):
        self.nanowidget.save()


class NaNoSidebar(QtGui.QPlainTextEdit):
    # Nano stuff including empty sidebar
    def __init__(self, path, get_filepath, get_text):
        QtGui.QLineEdit.__init__(self, None)
        self.setVisible(False)
        self.setReadOnly(True)
        self.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        font = QtGui.QFont()
        font.setFamily("Monospace")
        font.setPointSize(10)
        self.setFont(font)

        self.pluginpath = path
        self.get_text = get_text

        self.nano_width = 20 #TODO What is this?
        char_width = self.fontMetrics().averageCharWidth()
        self.setFixedWidth((self.nano_width + 1)*char_width)

        self.nano_day = 0 
        self.nano_mode = False

        cfg = common.read_json(os.path.join(self.pluginpath, 'cfg.json'))
        self.endpoint = cfg['nano']['endpoint']
        self.goal = int(cfg['nano']['goal'])
        self.days = int(cfg['nano']['days'])
        self.ideal_chapter = int(cfg['nano']['ideal_chapter'])
        self.cutoff_percent = int(cfg['nano']['cutoff_percent'])
        self.cutoff_minimum = int(cfg['nano']['cutoff_minimum'])
        self.cutoff_days = int(cfg['nano']['cutoff_days'])
        
        self.stats_dir = os.path.join(self.pluginpath, 'stats')
        self.get_filepath = get_filepath 

    def activate(self, arg):
        """
        Wrapper function to start NaNo mode.

        Called from terminal.
        """
        if arg.strip().isdigit():
            if int(arg.strip()) == 0:
                self.nano_mode = False
                return 'NaNo mode disabled', False
            elif int(arg.strip()) in range(1,self.days + 1):
                self.inano_day = int(arg.strip())
                self.nano_mode = True
                self.logfile_days = self.get_filepath() + '.logd'
                self.logfile_chapters = self.get_filepath() + '.logc'
                print(self.logfile_days)
                read_stats(self.nano_day, self.stats_dir)
                read_logs(self.logfile_days, self.nano_day)
                sb_text = update_sb(self.get_text(), self.endpoint, self.goal, 
                                    self.words_today, self.days, self.nano_day, 
                                    self.ideal_chapter, self.stats)
                self.setPlainText(sb_text)
                return 'NaNo mode initiated', False
            else:
                return 'Invalid date', True
        else:
            return 'Invalid argument', True
        
    def update_wordcount(self):
        if self.nano_mode:
            wcount = sum(self.count_words(self.endpoint, 
                         self.get_text())) 
        return wcount

    def save(self):
        if self.nano_mode:
            sb_text = update_sb(get_text(), self.endpoint, self.goal, 
                                self.words_today, self.days, self.nano_day, 
                                self.ideal_chapter, self.stats)
            self.setPlainText(sb_text)
            write_logs() #TODO args are /path/to/log_c, /path/to/log_d, self.nano_day, wordcount
            self.check_force_exit()
            #self.setPlainText(self.nanowidget.nanoGenerateStats())
            #self.nanoLogStats()

    def toggle_sidebar(self):
        """
        """
        if self.nano_mode:
            sb_text = update_sb(self.get_text(), self.endpoint, self.goal, 
                                self.words_today, self.days, self.nano_day, 
                                self.ideal_chapter, self.stats)
            self.setPlainText(sb_text)
            self.setVisible(abs(self.isVisible()-1))

    def check_force_exit(self):
        """
        check force-exit requirements from #1:
        a) a minimum wordcount per day that hasn't been reached 
           during a certain number of days in a row
        b) a minimum percentage of total wordcount hasn't been reached
        c) work has been nil for a certain number of days

        cutoff: percent, minimum, days
        """
        recent_days = [] #TODO See read_logs() for self.cutoff_days back
        day_goal = self.goal/self.days
        min_wordcount_reached = False        
        
        for day in recent_days:
            if day > day_goal * cutoff_minimum:
                min_wordcount_reached = True
                break
        if nano_day <= self.cutoff_days:
            min_wordcount_reached = True
        elif self.words > day_goal * nano_day * cutoff_minimum:
            min_wordcount_reached = True

        if not min_wordcount_reached:
            self.nano_mode = False
            #TODO Print error 'NaNo mode deactivated' (future pluginlib method)
            #TODO Do other shit also possibly?

def read_stats(nano_day, stats_dir):
    """
    Read logs from earlier years. 
    
    read_stats() replaces nanoExtractOldStats
    read old logs, extract stats from this day
        - file -> array
    """
    # if stats directory exists:
    stats = []
    if os.path.exists(stats_dir):
        raw_stats = os.listdir(self.stats_dir)
        for log in raw_stats:
            with open(log) as f:
                # daily_stats has lines of log for one year
                lines = f.readlines()
            stats_this_day = [log.split('.')] + [day.split(', ')[2] for day in lines if int(day.split(', ')[1]) == nano_day] 
            stats.append(stats_this_day)
        stats.sort()
    return stats 

def read_logs(logfile_days, nano_day):
    """
    Read log, return last recorded wordcount of day before nano_day.

    read_logs() replaces nanoCountWordsChapters + #12
    read current logs, #12
        - file -> array
    """
    #TODO Return last self.minimum_days of wcounts (for check_force_exit) 
    #TODO If log exists, do this, otherwise return 0
    with open(logfile_days) as f:
        log_lines = f.read().splitlines()
    logged_day = 0
    logged_words = 0
    for line in log_lines:
        logged_day = int(line.split(', ')[1])
        if logged_day < nano_day:
            logged_words = int(line.split(', ')[2])
        else:
            break
    return logged_words

def write_logs(source_file, logpath_c, logpath_d, day, chapters):
    """
    write_logs() replaces nanoLogStats
    write logs
        - array -> file
        - overwrite/non-overwrite, #21 
            The point is to keep the earliest of identical wordcounts.
    """
    filepath = source_file
    logfile_chapters = logpath_c
    logfile_dates = logpath_d
    dateform = '%Y-%m-%d %H:%M:%S'
    curr_date = datetime.datetime.now().strftime(dateform)
    curr_day = day
    curr_words = sum(chapters)
    
    # Replace chapters log with current chapter wordcounts
    head1 = 'STATISTICS FILE - CHAPTERS'
    head2 = 'CHAPTER = WORDS'
    chapter_head = '{}\n{}\n\n{}\n'.format(head1, filepath, head2)
    chapter_lines = ['{} = {}\n'.format(chapters.index(c), c) for c in chapters]
    with open(logfile_chapters, 'w') as logc:
        logc.write(''.join(chapter_lines))

    # Parse last line in dat logfile
    with open(logfile_dates, 'r') as logd:
        logd_line = logd.readlines()[-1].split('\n')[0]
    logd_day = int(logd_line.split(', ')[1].split(' = ')[0])
    logd_words = int(logd_line.split(', ')[1].split(' = ')[1])

    # Log current wordcount if it's not a duplicate
    if not (curr_day == logd_day and curr_words == logd_words):
        logline_d = '{}, {} = {}\n'.format(curr_date, curr_day, curr_words)
        with open(logfile_dates, 'a') as logd:
            logd.writeline(logline_d)



def count_words(raw_text, endpoint):
    """
    count_words() replaces nanoCountWordsChapters
    count words per chapter
    - exclude comments, #20
    - regex + file? -> array
    """
    # Join lines and remove comments.
    # Split into chapters at (newlines + chapter start)
    text = re.sub(r'\[.*?\]', '', raw_text, re.DOTALL)
    #TODO Maybe make chapter divisions less hard-coded?
    chapter_text = re.split(r'\n{3}(?=KAPITEL|CHAPTER)', text)
    # list comp, for each chapter:
    # remove words after endpoint
    # return length of given_chapter.split()
    # return total words as well?
    chapters = [len(re.findall(r'\S+', item)) 
                for item in chapter_text.split(endpoint)[0]]
    return chapters

def update_sb(raw_text, endpoint, goal, words_today, days, nano_day, ideal_chapter, stats):
    """
    update_sb() replaces nanoGenerateStats
    wordcounts -> sidebar

    Sidebar syntax:
        DAY nano_day
        % of total goal

        Chapter Words Remaining
        ...     ...   ...

        Total
        Remaining today
        Written today
        Earlier years:
        Year diff_from_this_year
    """
    #NOTE Handle width of sidebar
    form = '{}' #NOTE This should be that thing with right-justified shit
    chapters = count_words(raw_text, endpoint) 
    percent = total/goal
    diff_today = words_today - (goal - sum(chapters))/(days - nano_day)
    text = 'DAY {0}, {1:.2%}\n\n'.format(nano_day, percent)  
    for item in chapters:
        line = '{} {} {}\n'.format(chapters.index(item), item, 
                                   item - ideal_chapter)
        text += line
    text += '\nTOTAL {}\n'.format(sum(chapters))
    text += 'Today {}\n'.format() #NOTE What's the variable called?
    text += 'Todo {}\n'.format(diff_today)
    text += '\nEarlier stats\n'
    for item in stats:
        line = '{} {}\n'.format(item[0], item[1])
        text += line
    return text

