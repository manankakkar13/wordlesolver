#!/usr/bin/env python3

import string
import sys
import json
import requests
import argparse
from tkinter.messagebox import NO
from typing import List

from utility import Utility
from dataclasses import dataclass


@dataclass
class SuggestedWordsResults:
    words:List[str]
    word_list_file_path:str = None


class WorldSolverMultiList:

    def __init__(self, word_list_file_paths: list = [], word_length : int = 5, exclude_plurals:bool=True, word_socres:dict={}, order_words_by_score_desc:bool=False, word_symbol_combinations:dict={}):
        self.word_lists = []
        self.word_list_file_paths = word_list_file_paths
        self.word_length = word_length
        self.exclude_plurals = exclude_plurals
        self.word_socres = word_socres
        self.max_try_indexes_for_lists = []
        self.order_words_by_score_desc = order_words_by_score_desc
        self.word_symbol_combinations = word_symbol_combinations
        for file_path in self.word_list_file_paths:
            word_list = Utility.load_word_list(file_path, self.word_length, self.exclude_plurals)
            self.word_lists.append(word_list)
        self.reset()
        pass


    def reset(self):
        self.tries = []
        self.solvers = []
        for word_list in self.word_lists:
            solver = WordleSolver(None, self.word_length, self.exclude_plurals)
            solver.word_list = word_list
            solver.word_socres = self.word_socres
            solver.order_words_by_descending_socre = self.order_words_by_score_desc
            solver.word_symbol_combinations = self.word_symbol_combinations
            self.solvers.append(solver)
        pass


    def reset_pattern_parameters(self):
        for solver in self.solvers:
            solver.reset()
        pass


    def get_pattern_parameter_conflicts(self):
        if len(self.solvers) > 0:
            # conflict check results should be the identical across solvers.
            # it is alright to return conflicts detected from the first sovler only
            return self.solvers[0].get_pattern_parameter_conflicts()
        raise Exception("No solvers")


    def update_pattern_paramters(self):
        for solver in self.solvers:
            solver.tries = self.tries
            solver.update_pattern_paramters()
        pass

    
    def input_guess_result(self, word, result_symbols):
        for solver in self.solvers:
            solver.input_guess_result(word, result_symbols)
        self.tries.append((word, result_symbols))
        pass


    def get_suggested_words(self) -> SuggestedWordsResults:
        for i in range(0, len(self.solvers)):
            if len(self.max_try_indexes_for_lists) >= len(self.solvers):
                if len(self.tries) >= self.max_try_indexes_for_lists[i]:
                    continue
            suggested_words = self.solvers[i].get_suggested_words()
            if len(suggested_words) > 0:
                return SuggestedWordsResults(suggested_words, self.word_list_file_paths[i])
        last_word_list_file_path = None if len(self.word_list_file_paths) <= 0 else self.word_list_file_paths[-1]
        return SuggestedWordsResults([], last_word_list_file_path)

    
    def set_excluded_words(self, excluded_words:list):
        for solver in self.solvers:
            solver.excluded_words = excluded_words
        pass


class WordleSolver():

    def __init__(self, word_list_file_path: str = None, word_length : int = 5, exclude_plurals:bool=True):
        self.permitted_input_symbols = "+?_"
        self.word_list = []
        self.word_socres = {}
        self.word_symbol_combinations = {}
        self.symbol_anyletter = "*"
        self.effective_word_list = []
        self.word_list_file_path = word_list_file_path
        self.word_length = word_length
        self.exclude_plurals = exclude_plurals
        self.order_words_by_descending_socre = False
        if self.word_list_file_path is not None:
            self.word_list = Utility.load_word_list(self.word_list_file_path, self.word_length, self.exclude_plurals)
        self.reset()

    def reset(self):
        self.tries = []
        self.reset_pattern_parameters()


    def reset_pattern_parameters(self):
        self.included_letters = ""
        self.excluded_letters = ""
        self.high_prob_letters = ""
        self.wrong_spot_pattern = [""] * self.word_length
        self.right_spot_pattern = self.symbol_anyletter * self.word_length
        self.max_letter_occurrence = {}
        self.excluded_words = []
        self.effective_word_list = []


    def get_pattern_parameter_conflicts(self):
        conflicts = []
        for letter in self.excluded_letters:
            if letter in self.included_letters + self.high_prob_letters:
                conflicts.append((letter, "excluded letter found in inclusion list"))
            if letter in self.right_spot_pattern:
                conflicts.append((letter, "excluded letter found in right spot pattern"))
        for i in range(0, self.word_length):
            if self.right_spot_pattern[i] in self.wrong_spot_pattern[i]:
                conflicts.append((letter, "letter in right spot found in wrong spot pattern"))
        return conflicts
    

    def update_pattern_paramters(self):
        self.reset_pattern_parameters()
        possible_word_lists = []
        for (word, symbol_pattern) in self.tries:
            for i in range(0, self.word_length):
                if symbol_pattern[i] in ["+", "?"]:
                    self.included_letters += word[i]
                    if symbol_pattern[i] == "+":
                        right_spot_pattern_list = list(self.right_spot_pattern)
                        right_spot_pattern_list[i] = word[i]
                        self.right_spot_pattern = "".join(right_spot_pattern_list)
                    elif symbol_pattern[i] == "?":
                        self.wrong_spot_pattern[i] += word[i]
                elif symbol_pattern[i] == "_":
                    if word[i] not in self.included_letters:
                        self.excluded_letters += word[i]
                    else:
                        if word[i] not in self.max_letter_occurrence:
                           self.max_letter_occurrence[word[i]] = sum([1 for letter in word[:i] if letter == word[i]]) + sum([1 for letter in word[(i+1):] if letter == word[i]])
            if word in self.word_symbol_combinations:
                if symbol_pattern in self.word_symbol_combinations[word]:
                    possible_word_lists.append(self.word_symbol_combinations[word][symbol_pattern])
        self.included_letters = "".join(set(self.included_letters))
        self.excluded_letters = "".join(set([letter for letter in self.excluded_letters if letter not in self.included_letters]))
        self.wrong_spot_pattern = ["".join(set(pattern)) for pattern in self.wrong_spot_pattern]
        if len(possible_word_lists) > 0:
            effective_words_set = []
            for possible_word_list in possible_word_lists:
                effective_words_set += possible_word_list
            effective_words_set = list(set(effective_words_set))
            self.effective_word_list = [word for word in effective_words_set if all([word in word_list for word_list in possible_word_lists])]
        pass


    def get_letter_prob_dict(self, word_list):
        if len(word_list) <= 0:
            return []

        letter_freq_dict = {}
        for letter in string.ascii_lowercase:
            letter_freq_dict[letter] = 0

        for word in word_list:
            for letter in word:
                letter_freq_dict[letter] += 1

        letter_prob_dict = {}
        total_letters = sum([len(word) for word in word_list])

        for letter in letter_freq_dict.keys():
            letter_prob_dict[letter] = (letter_freq_dict[letter] / total_letters)

        return letter_prob_dict


    def get_suggested_letters_by_freq(self, possible_words):
        if len(possible_words) <= 0:
            return []
        letter_freqs = [(letter, prob) for _, (letter, prob) in enumerate(self.get_letter_prob_dict(possible_words).items()) if letter not in self.included_letters + self.excluded_letters + self.high_prob_letters]
        return letter_freqs


    def get_letter_positional_prob_dict(self, words):
        positional_prob = []
        for i in range(0, len(self.right_spot_pattern)):
            if self.right_spot_pattern[i] == self.symbol_anyletter:
                letter_list = [word[i] for word in words]
                positional_prob.append(self.get_letter_prob_dict(letter_list))
            else:
                positional_prob.append({})
        return positional_prob


    def sort_words_with_letter_positional_prob(self, words):
        letter_position_prob = self.get_letter_positional_prob_dict(words)
        words_with_prob = []
        for word in words:
            score = 1
            for i in range(0, len(letter_position_prob)):
                if letter_position_prob[i]:
                    score *= letter_position_prob[i][word[i]]
            words_with_prob.append((word, score))
        words_with_prob.sort(key=lambda element: element[1], reverse=True)
        return words_with_prob


    def sort_words(self, words):
        sorted_words = []
        if len(self.word_socres) > 0:
            if all([word in self.word_socres for word in words]):
                words_with_socres = [(word, self.word_socres[word]) for word in words]
                words_with_socres.sort(key=lambda element: element[1], reverse=self.order_words_by_descending_socre)
                sorted_words = [word for (word, _) in words_with_socres]
        if len(sorted_words) <= 0:
            sorted_words = [word_with_prob[0] for word_with_prob in self.sort_words_with_letter_positional_prob(words)]
        return sorted_words


    def is_not_in_word(self, word):
        return all([letter not in word for letter in self.excluded_letters])

    def is_in_word(self, word):
        return all([letter in word for letter in self.included_letters + self.high_prob_letters])

    def is_not_tried(self, word):
        return word not in self.tries

    def match_right_spot_pattern(self, word):
        for i in range(0, len(self.right_spot_pattern)):
            if self.right_spot_pattern[i] == self.symbol_anyletter:
                continue
            elif self.right_spot_pattern[i] != word[i]:
                return False
        return True
    

    def get_possible_words(self):
        if len(self.effective_word_list) <= 0:
            self.effective_word_list = self.word_list
        all_excluded_words = list(set([attempt[0] for attempt in self.tries] + self.excluded_words))
        first_level_filter = [word for word in self.effective_word_list if self.is_in_word(word) and self.is_not_in_word(word) and self.is_not_tried(word) and word not in all_excluded_words]
        second_level_filter = [word for word in first_level_filter if all([word[i] not in self.wrong_spot_pattern[i] for i in range(0, self.word_length)])]
        third_level_filter = [word for word in second_level_filter if self.match_right_spot_pattern(word)]
        if len(self.max_letter_occurrence) <= 0:
            return third_level_filter
        else:
            for letter in self.max_letter_occurrence.keys():
                fourth_level_filter = [word for word in third_level_filter if sum([1 for l in word if l == letter]) <= self.max_letter_occurrence[letter]]
            return fourth_level_filter


    def get_suggested_words(self):
        all_possible_words = self.get_possible_words()
        if len(all_possible_words) <= 0:
            return []
        unknown_letter_count = self.word_length - len(self.included_letters)
        suggested_letters_with_prob = self.get_suggested_letters_by_freq(all_possible_words)
        if len(suggested_letters_with_prob) <= 0:
            return []
        suggested_letters_with_prob.sort(key=lambda element: element[1], reverse=True)
        suggested_letters = list([letter for (letter, prob) in suggested_letters_with_prob])
        for i in range(unknown_letter_count, 0, -1):
            self.high_prob_letters = suggested_letters[:i]
            self.update_pattern_paramters()
            suggested_words = self.get_possible_words()
            self.high_prob_letters = ""
            if len(suggested_words) > 0:
                suggested_words = self.sort_words(suggested_words)
                return suggested_words
        all_possible_words = self.sort_words(all_possible_words)
        return all_possible_words


    def input_guess_result(self, word, result_symbols):
        if len(word) != self.word_length or len(result_symbols) != self.word_length:
            raise Exception("Word length or symbol length is invalid")
        if not all([character in string.ascii_lowercase for character in word]):
            raise Exception("Word contains invalid character")
        if not all([symbol in self.permitted_input_symbols for symbol in result_symbols]):
            raise Exception("Symbols contains an invalid symbol")
        self.tries.append((word, result_symbols))
        self.update_pattern_paramters()


#argParser = argparse.ArgumentParser()

#argParser.add_argument("--length", help="The length (number of letters) of the hidden word", required=False, default=5, type=int)
#argParser.add_argument("--plurals", help="Do not exclude plurals when loading from the word list", required=False, default=False, type=bool)

#args = argParser.parse_args()

word_list_file_paths = ["english_words_opener.txt", "english_words_full.txt"]

solver_multi = WorldSolverMultiList(word_list_file_paths)

solver_multi.max_try_indexes_for_lists = [2, sys.maxsize]

# print("The WORDLE Solver CLI")
# #print(f"(Word length: {args.length}; Plurals: {'Yes' if args.plurals else 'No'})")
# print("Press CTRL+C to exit\n")
# print("Meanings of symbols:")
# print(" +\tletter in the word and in the right spot (green box)")
# print(" ?\tletter in the word but in a wrong spot (orange box)")
# print(" _\tletter not in the word (grey box)\n")
# print("Commands:")
# print(" !done\t\tyou're done guessing a hidden word.  this will reset the state of the solver for you to guess a new hidden word")
# print(" !tries\t\tsee the tries entered")
# print(" !remove_last\tremove the last try entered\n")
# print(sys.argv[1])
first_run = True
words = sys.argv
#print(words)
res = []
for i in range(1, len(sys.argv)):
    w = (sys.argv[i])
    #print(w)
    # print("Please enter you last try as word:symbols")
    user_input = w
    # print(user_input)
    reset = False

    if ":" in user_input:
        values = user_input.split(":")
        if len(values) < 2:
            print("Invalid format")
            continue
        if not all([len(value) == solver_multi.word_length for value in values]):
            print("Invalid format: length of word or symbol is incorrect")
            continue
        if values[1] == "+" * solver_multi.word_length:
            print("Great!")
            reset = True
        else:
            solver_multi.input_guess_result(values[0], values[1])
            conflicts = solver_multi.get_pattern_parameter_conflicts()
            if len(conflicts) > 0:
                for conflict in conflicts:
                    print(f"{conflict[0]}: {conflict[1]}")
                solver_multi.tries = solver_multi.tries[:-1]
                print("Your last try has been removed")
                continue
    elif (user_input == "!done"):
        reset = True
    elif (user_input == "!remove_last"):
            solver_multi.tries = solver_multi.tries[:-1]
            print("Your last try has been removed")
            continue
    elif (user_input == "!tries"):
        if len(solver_multi.tries) <= 0:
            print("No tries entered")
        else:
            for i in range(0, len(solver_multi.tries)):
                print(f"\tTry {i}: {solver_multi.tries[i]}")
        continue
    else:
        print("Invalid input")


    if reset:
        solver_multi.reset()
        print("The state is reset")
        continue

    suggested_words = solver_multi.get_suggested_words()

if len(suggested_words.words) > 0:
    # print(f"Suggested words (from list '{suggested_words.word_list_file_path}'):")
    for suggestion in suggested_words.words[:10]:
        res.append(suggestion)
        # print(f"\t{suggestion}")
    # print("Sorry, no other possible words.  Please check the result symbols you entered.")

    

print(res)
sys.stdout.flush()
