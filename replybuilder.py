# Name:             Sentence Generator
# Description:      Generates sentences based on what Emma knows about English and the world
# Section:          REPLY
import random
import re

import pattern.en
import sqlite3 as sql
import enchant
from colorama import init, Fore
init(autoreset = True)

import utilities
import settings

connection = sql.connect('emma.db')
cursor = connection.cursor()

mood = int

def generate_sentence(tokenizedMessage, moodAvg, askerIntents=[{'declarative': True, 'interrogative': False, 'greeting': False}], asker="", questionPackages=[]):
    print "Creating reply..."
    global mood
    mood = moodAvg

    print "Determining important words..."
    importantWords = []
    for sentence in tokenizedMessage:
        for word in sentence:
            if word[1] in utilities.nounCodes and word[3] and word[0] not in importantWords: importantWords.append(word[0])
    if len(importantWords) == 0: 
        # Fail state
        print Fore.RED + "No important words were found in the input. Sentence generation failed."
        return "%"

    # Find and bundle associations
    print "Creating association bundles..."
    associationBundle = bundle_associations(importantWords)

    # Create an association package from the bundles
    print "Packaging association bundles and related information..."
    associationPackage = make_association_package(associationBundle, asker)
    if len(associationPackage[1]) == 0: 
        # Fail state
        print Fore.RED + "There are no associations available to generate a reply. Sentence generation failed."
        return "%"

    # Generate the reply
    hasGreeting = False
    for intent in askerIntents:
        if intent['greeting']: hasGreeting = True

    # Attempt to generate answers if we have any
    # todo: merge this with the answer formatting code a few lines down
    answerPackages = []
    for question in questionPackages: answerPackages.append(make_answer_package(question))

    # Decide how many sentences we want to generate. If we're answering a question, generate fewer sentences
    if len(answerPackages) == 0: sentencesToGenerate = random.randint(1, 3)
    else: sentencesToGenerate = random.randint(0, 1)

    formattedAnswers = []
    for answer in answerPackages:
        answer = format_answer(answer)
        answer.append(random.choice([u"!", u"."]))
        answers.extend(answer)

 	# All words start with an equal chance of being chosen for sentence generation. If the word is used, its chance of being chosen decreases by 1 each time it's used until it reaches 0
    wordList = {}
    for associationBundle in associationPackage[1]: wordList[associationBundle['word']] = 3

    # Choose what domains to include in the sentence and order them correctly
    print "Generating %d domains..." % sentencesToGenerate
    domains = []
    for i in range(0, sentencesToGenerate):
        if mood >= 0.1 and hasGreeting and associationPackage[0]['asker'] != "" and i == 0: domains.append(("=GREETING", associationPackage[0]['asker'], []))

        # Choose the word to use as the seed for our sentence based on weighted random chance
        wordDistribution = []
        for word in wordList.keys(): wordDistribution.extend([word] * wordList[word])
        word = random.choice(wordDistribution)
        wordList[word] -= 1     # Decrease the chance of this word being chosen again
        
        if len(wordDistribution) > 0:
            # Create list intents to choose from, and choose an intent from it
            validIntents = determine_valid_intents(associationPackage)
            intent = random.choice(validIntents[word])

            # Retrieve our chosen word's association group
            for associationGroupIter in associationPackage[1]:
                if associationGroupIter['word'] == word: 
                    print associationGroupIter
                    associationGroup = associationGroupIter
                    print "Domain " + str(i + 1) + ": " + intent + " for \'" + word + "\' with " + str(len(associationGroup['associations'])) + " associations"
                    break

            # Decide whether to make objects in the sentence plural
            global pluralizeObjects
            if random.randint(0, 1) == 0 and enchant.Dict('en_US').check(pattern.en.pluralize(word)): 
                with connection:
                    cursor.execute("SELECT part_of_speech FROM dictionary WHERE word = \'%s\';" % word)
                    if cursor.fetchall()[0] not in ["NNP", "NNPS"]: pluralizeObjects = True
            else: pluralizeObjects = False

            domains.append(("=" + intent, word, associationGroup))
        else: break

    # Sort the domains
    sortedDomains = []
    for domain in domains:
        if domain[0] == "=GREETING": sortedDomains.append(domain)
    for domain in domains:
        if domain[0] == "=DECLARATIVE": sortedDomains.append(domain)
    for domain in domains:
        if domain[0] == "=IMPERATIVE": sortedDomains.append(domain)
    for domain in domains:
        if domain[0] == "=PHRASE": sortedDomains.append(domain)
    for domain in domains:
        if domain[0] == "=INTERROGATIVE": sortedDomains.append(domain)
    domains = sortedDomains

    # Use our domain template to create the reply
    reply = []
    for count, domain in enumerate(domains):
        sentence = []
        print Fore.MAGENTA + "Generating sentence %d of %d..." % (count + 1, len(domains))

        # Decide how to proceed with sentence generation based on our intent
        if domain[0] == '=GREETING': sentence = make_greeting(domain[1]) + [u"!"]
        elif domain[0] == '=PHRASE': sentence = make_phrase(domain[2]) + [u"."]
        elif domain[0] == '=IMPERATIVE': sentence = make_imperative(domain[2]) + [u"."]
        elif domain[0] == '=INTERROGATIVE': sentence = make_interrogative(domain[1]) + [u"?"]
        elif domain[0] == '=DECLARATIVE': 
            if random.randint(0, 1) == 0: sentence = make_declarative(associationGroup) + [u"."]        # Create a declarative sentence
            else:
                # Create a comparative sentence
                comparisonCandidatesList = {}
                for word in validIntents.keys():
                    if 'DECLARATIVE' in validIntents[word]: comparisonCandidatesList[word] = wordList[word]

                comparisonDistribution = []
                for word in comparisonCandidatesList.keys(): comparisonDistribution.extend([word] * comparisonCandidatesList[word])
                comparison = random.choice(comparisonDistribution)
                wordList[comparison] -= 1       # Decrease the chance of the compared word being chosen again

                for comparisonAssociationGroup in associationPackage[1]:
                    if comparisonAssociationGroup['word'] == comparison: comparisonGroup = comparisonAssociationGroup
                sentence = make_comparative(associationGroup, comparisonGroup) + [u"."]
            
        print ' '.join(sentence)
        reply.extend(sentence)
    
    print "Finalizing reply..."
    if answers != []:
        reply = reply + answers
    return finalize_reply(reply)

def find_associations(word):
    # Finds and returns the input word's associations
    associationGroup = []
    with connection:
        cursor.execute("SELECT * FROM associationmodel WHERE word = \"%s\";" % re.escape(word))
        SQLReturn = cursor.fetchall()
    if SQLReturn:
        for row in SQLReturn: associationGroup.append({'type': row[1], 'target': row[2], 'weight': row[3]})
    return associationGroup

def bundle_associations(words):
    associationBundle = []
    print Fore.GREEN + u"Finding associations for:",
    for word in words:
        print word,
        associationBundle.append((word, find_associations(word)))
    print Fore.GREEN + u"[Done]"
    return associationBundle
    
def make_association_package(associationBundle, asker):
    associationPackage = []
    for associationGroup in associationBundle:
        hasHas = False
        hasIsA = False
        hasHasProperty = False
        hasHasAbilityTo = False
        hasHasObject = False
        for association in associationGroup[1]:
            if association['type'] == "HAS": hasHas = True
            if association['type'] == "IS-A": hasIsA = True
            if association['type'] == "HAS-PROPERTY": hasHasProperty = True
            if association['type'] == "HAS-ABILITY-TO": hasHasAbilityTo = True
            if association['type'] == "HAS-OBJECT": hasHasObject = True

        associationPackage.append({
            'word': associationGroup[0], 
            'hasHas': hasHas, 
            'hasIsA': hasIsA, 
            'hasHasProperty': hasHasProperty,
            'hasHasAbilityTo': hasHasAbilityTo,
            'hasHasObject': hasHasObject,
            'associations': associationGroup[1]
            })
    numObjects = len(associationBundle)
    associationPackage = ({'asker': asker, 'numObjects': numObjects}, associationPackage)
    return associationPackage

def make_answer_package(questionPackage):
    answer = tuple
    print u"Question package:" + str(question)
    # "WHAT IS THE [ADJECTIVE] OF [NOUN]"
    if question[0] == "what":
        with connection:
            cursor.execute("SELECT * FROM associationmodel WHERE word = \'%s\' AND association_type = \'HAS-PROPERTY\';" % question[2])
            answerCandidates = []

            for adjective in cursor.fetchall():
                cursor.execute("SELECT * FROM associationmodel WHERE word = \'%s\' AND target = \'%s\';" % (adjective[2], question[1]))
                SQLReturn = cursor.fetchone() 
                if SQLReturn != []:
                    answerCandidates = (SQLReturn)

            if len(answerCandidates) > 0:
                answer = answerCandidates[0]
                # Choose the answer with the highest weight
                for candidate in answerCandidates:
                    if candidate[3] > answer[3]: answer = candidate
                answer = ("what", question[1], question[2], answer[0])      # (what) COLOR (of) SKY (be) ANSWER
    
    # "DO [NOUN] HAVE [NOUN]"
    if question[0] == "doXhaveY":
        with connection:
            cursor.execute("SELECT * FROM associationmodel WHERE word = \'%s\' AND association_type = \'HAS\' AND target = \'%s\';" % (question[1], question[2]))
            SQLReturn = cursor.fetchone()
            # todo: add lower bound?
            
            if SQLReturn != []: answer = ("does", question[1], question[2], True)       # yes/no, CATS (have) PAWS
            else: answer = ("does", question[1], question[2], False)

    # "CAN [NOUN] [VERB]"
    if question[0] == "can":
        with connection:
            cursor.execute("SELECT * FROM associationmodel WHERE word = \'%s\' AND association_type = \'HAS-ABILITY-TO\' AND target = \'%s\';" % (question[1], question[2]))
            SQLReturn = cursor.fetchone()
            # todo: add lower bound?

            if SQLReturn != []: answer = ("can", question[1], question[2], True)        # yes/no, EMMA (can) CREATE
            else: answer = ("can", question[1], question[2], False)
    return answer

def determine_valid_intents(associationPackage):
    # This function doesn't include interrogatives or greetings, since those are Association Bundle-specific
    validIntents = {}
    for associationBundle in associationPackage[1]:
        intents = ['PHRASE']
        if associationBundle['hasHas'] or associationBundle['hasIsA'] or associationBundle['hasHasProperty'] or associationBundle['hasHasAbilityTo']: intents.append('DECLARATIVE')
        if len(associationBundle['associations']) < 3 and associationBundle['word'] != associationPackage[0]['asker']: intents.append('INTERROGATIVE')
        if associationBundle['hasHasAbilityTo']: intents.append('IMPERATIVE')
        validIntents[associationBundle['word']] = intents
    return validIntents

def choose_association(associationGroup):
    dieSeed = 0
    for association in associationGroup: dieSeed += association['weight']
    dieResult = random.uniform(0, dieSeed)

    for association in associationGroup:
        dieResult -= association['weight']
        if dieResult <= 0: return association

def format_answer(answer):
    print answer
    answerDomains = []
    if answer[0] == "what": answerDomains = [
            [u"The", answer[1], u"of", u"the", answer[2], u"is", answer[3]]
        ]
    elif answer[0] == "does":
        if answer[3]: answerDomains = [
            [u"Yes"],
            [u"I", u"think", u"so", u",", u"yes"],
            [answer[1], u"have", answer[2]],
            [u"Yes", answer[1], u"have", answer[2]]
        ]
        else: answerDomains = [
            [u"No"],
            [u"I", u"don\'t", u"think", u"so"],
            [answer[1], u"do", u"not", u"have", answer[2]],
            [u"no", answer[1], u"don\'t", u"have", answer[2]]
        ]
    elif answer[0] == "can":
        if answer[3]: answerDomains = [
            [u"Yes"],
            [u"I", u"think", u"so", u",", u"yes"],
            [u"Yes", u",", answer[1], u"can", answer[2]],
            [answer[1], u"can", answer[2]]
        ]
        else: answerDomains = [
            [u"No"],
            [u"I", u"don\'t", u"think", u"so"],
            [answer[1], u"can", u"not", answer[2]],
            [u"No", u",", answer[1], u"can", u"not", answer[2]],
            [answer[1], u"can\'t", answer[2]],
            [u"No", u",", answer[1], u"can\'t", answer[2]]
        ]

    domain = random.choice(answerDomains)

    if settings.option('general', 'verboseLogging'): print "Building an answer..."
    sentence = domain

    return sentence

def make_greeting(asker):
    if settings.option('general', 'verboseLogging'): print "Generating a greeting..."
    greetingDomains = [
        [u"Hi", asker], 
        [u"Hello", asker]
    ]
    return random.choice(greetingDomains)

def make_comparative(associationGroup, comparisonGroup):
    if settings.option('general', 'verboseLogging'): print "Generating a comparative statement for \'%s\' and \'%s\'..." % (associationGroup['word'], comparisonGroup['word'])

    comparativeDomains = [
        [u"=DECLARATIVE", u"like", u"=COMPARISON"],
        [u"=DECLARATIVE", u",", u"and", u"=COMPARISON"],
        [u"=DECLARATIVE", u",", u"but", u"=COMPARISON"]
    ]
    domain = random.choice(comparativeDomains)

    if settings.option('general', 'verboseLogging'): print "Building comparative statement..."
    sentence = []
    for count, slot in enumerate(domain):
        print ' '.join([' '.join(sentence), ' '.join(domain[count:])])
        if slot == u"=DECLARATIVE": sentence.extend(make_declarative(associationGroup))
        elif slot == u"=COMPARISON": sentence.extend(make_declarative(comparisonGroup))
        else: sentence.append(slot)

    return sentence

def make_declarative(associationGroup):
    if settings.option('general', 'verboseLogging'): print "Generating a declarative statement for \'%s\'..." % associationGroup['word']
    
    # Gather information about what associations we have to help us decide what domains we're allowed to use
    hasAssociations = []
    isaAssociations = []
    haspropertyAssociations = []
    hasabilitytoAssociations = []
    for association in associationGroup['associations']:
        if association['type'] == "HAS": hasAssociations.append(association)
        if association['type'] == "IS-A": isaAssociations.append(association)
        if association['type'] == "HAS-PROPERTY": haspropertyAssociations.append(association)
        if association['type'] == "HAS-ABILITY-TO": hasabilitytoAssociations.append(association)

    declarativeDomains = []
    if haspropertyAssociations != []: declarativeDomains.append(
        [u"=PHRASE", u"=ISARE", u"=ADJECTIVE"]
    )
    if len(haspropertyAssociations) > 1: declarativeDomains.append(
        [u"=PHRASE", u"=ISARE", u"=ADJECTIVE", u"and", u"=ADJECTIVE"]
    )
    if hasabilitytoAssociations != []: declarativeDomains.extend([
        [u"=PHRASE", u"=VERB"],
        [u"=PHRASE", u"can", u"=VERB"]
    ])
    if hasAssociations != []: declarativeDomains.append(
        [u"=PHRASE", u"=HAVEHAS", u"=PHRASE-HAS"]
    )
    if isaAssociations != []: declarativeDomains.append(
        [u"=PHRASE", u"=ISARE", u"=PHRASE-IS-A"]
    )
    domain = random.choice(declarativeDomains)

    if settings.option('general', 'verboseLogging'): print "Building declarative statement..."
    sentence = []
    # Iterate through the objects in the domain and fill them in to create the declarative statement
    for count, slot in enumerate(domain):
        print ' '.join([' '.join(sentence), ' '.join(domain[count:])])
        if slot == u"=PHRASE": sentence.extend(make_phrase(associationGroup))
        elif slot == u"=ADJECTIVE": sentence.append(choose_association(haspropertyAssociations)['target'])
        elif slot == u"=VERB": sentence.append(choose_association(hasabilitytoAssociations)['target'])       #todo: add "how" ("the snake moved (how?) quickly")
        elif slot == u"=PHRASE-HAS": sentence.append(choose_association(hasAssociations)['target'])
        elif slot == u"=PHRASE-IS-A": sentence.append(choose_association(isaAssociations)['target'])
        elif slot == u"=ISARE":
            if pluralizeObjects: sentence.append(u"are")
            else: sentence.append(u"is")
        elif slot == u"=HAVEHAS":
            if pluralizeObjects: sentence.append(u"have")
            else: sentence.append(u"has")
        else: sentence.append(slot)

    return sentence

def make_imperative(associationGroup):
    if settings.option('general', 'verboseLogging'): print "Generating an imperative statement for \'%s\'..." % associationGroup['word']

    # Decide what verb to use
    verbBundle = []
    for association in associationGroup['associations']:
        if association['type'] == "HAS-ABILITY-TO": verbBundle.append(association)
    verb = choose_association(verbBundle)['target']

    # See if the verb has any objects and gather them into their own bundle
    associationBundle = bundle_associations([verb])
    objectBundle = []
    for association in associationBundle[0][1]:
        if association['type'] == "HAS-OBJECT": objectBundle.append(association)

    imperativeDomains = [
        [u"=VERB"]
    ]
    if len(objectBundle) > 0:
        imperativeDomains.append(
            [u"=VERB", u"=OBJECT"]
        )
        if mood > 0: imperativeDomains.append(
            [u"always", u"=VERB", u"=OBJECT"]
        )
        else: imperativeDomains.append(
            [u"never", u"=VERB", u"=OBJECT"]
        )
    else:
        if mood > 0: imperativeDomains.append(
            [u"always", u"=VERB"]
        )
        else: imperativeDomains.append(
            [u"never", u"=VERB"]
        )
    # todo: new domain: VERB a/an/the OBJECT with (its THING OBJECT HAS / a/an/the OTHER OBJECT)
    domain = random.choice(imperativeDomains)
    
    if settings.option('general', 'verboseLogging'): print "Building imperative statement..."
    sentence = []
    if mood > 0.4: 
        if random.randint(0, 1) == 0: sentence = [u"please"]

    for count, slot in enumerate(domain):
        print ' '.join([' '.join(sentence), ' '.join(domain[count:])])
        if slot == "=OBJECT": sentence.append(choose_association(objectBundle)['target'])
        elif slot == "=VERB": sentence.append(verb)
        else: sentence.append(slot)

    return sentence

def make_interrogative(word):
    if settings.option('general', 'verboseLogging'): print "Generating an interrogative phrase for \'%s\'..." % word

    interrogativeDomains = [
        [u"what\'s", u"=WORD"]
    ]
    if pluralizeObjects: interrogativeDomains.append(
        [u"what", u"are", u"=WORD"]
    )
    else: interrogativeDomains.extend([
        [u"what", u"is", u"=WORD"],
        [u"what", u"is", u"a", u"=WORD"]
    ])
    domain = random.choice(interrogativeDomains)

    if settings.option('general', 'verboseLogging'): print "Building interrogative phrase..."
    sentence = []
    for count, slot in enumerate(domain):
        print ' '.join([' '.join(sentence), ' '.join(domain[count:])])
        if slot == u"=WORD":
            if pluralizeObjects: sentence.append(pattern.en.pluralize(word))
            else: sentence.append(word)
        else: sentence.append(slot)

    return sentence

def make_phrase(associationGroup):
    if settings.option('general', 'verboseLogging'): print "Generating a phrase for \'%s\'..." % associationGroup['word']
    
    if settings.option('general', 'verboseLogging'): print "Looking for adjective associations..."
    adjectiveAssociations = []
    for association in associationGroup['associations']:
        if association['type'] == "HAS-PROPERTY": adjectiveAssociations.append(association)

    phraseDomains = [
        [u"=OBJECT"]
    ]
    if len(adjectiveAssociations) >= 1: phraseDomains.append(
        [u"=ADJECTIVE", u"=OBJECT"]
    )
    if len(adjectiveAssociations) > 1: phraseDomains.append(
        [u"=ADJECTIVE", u"=ADJECTIVE", u"=OBJECT"]
    )
    domain = random.choice(phraseDomains)

    if settings.option('general', 'verboseLogging'): print "Building phrase..."
    # Decide if we want to precede the phrase with a determiner ("the", "a")
    if random.randint(0, 1) == 0: 
        determiners = [[u"the"]]
        if pluralizeObjects: determiners.extend([[u"some"], [u"many"]])
        else: determiners.append([u"a"])
        sentence = random.choice(determiners)
    else: sentence = []

    # Iterate through the objects in the domain and fill them in to create the phrase
    for count, slot in enumerate(domain):

        print ' '.join([' '.join(sentence), ' '.join(domain[count:])])
        if slot == u"=OBJECT":
            if pluralizeObjects: sentence.append(pattern.en.pluralize(associationGroup['word']))
            else: sentence.append(associationGroup['word'])
        elif slot == u"=ADJECTIVE": sentence.append(choose_association(adjectiveAssociations)['target'])
    
    return sentence

def finalize_reply(reply):
    # todo: optimize this function
    splitReply = pattern.en.parse(' '.join(reply), True, True, False, False, True).split()
    tokenizedReply = []
    for sentence in splitReply: tokenizedReply.extend(sentence)     # Fix some pattern.en formatting stuff
    
    lastUsedNouns = []
    for count, word in enumerate(tokenizedReply):
        # If we repeat proper nouns, refer back to them with "they"
        if word[1] in utilities.nounCodes:
            if tokenizedReply[count - 1][0] in [u".", u"!", u"?", u"and", u"but"]:
                if word[2] in lastUsedNouns[:2] and tokenizedReply[count + 1][1] != u".":
                    tokenizedReply[count][0] = u"they"
            lastUsedNouns.append(word[2])

        # Refer to Ellie and Alex as mom and dad
        if u"sharkthemepark" in word[0]: tokenizedReply[count][0] = u"mom"
        elif u"nosiron" in word[0]: tokenizedReply[count][0] = u"dad"

    reply = []
    for word in tokenizedReply:
        reply.append(word[0])
    
    # Correct positions of punctuation, capitalize first letter of first word in new sentences
    reply[0] = reply[0][0].upper() + reply[0][1:]
    for count, word in enumerate(reply):
        if word in [u"\'s", u"n\'t"]:
            reply[count - 1] += word
        elif word in [u".", u",", u"!", u"?"]:
            reply[count - 1] += word
            if word in [u".", u"!", u"?"] and count + 1 != len(reply):
                reply[count + 1] = reply[count + 1][0].upper() + reply[count + 1][1:]

    print reply
    
    reply[:] = [word for word in reply if word not in [u".", u",", u"!", u"?", u"\'s", u"\'s." u"n\'t"]]

    return ' '.join(reply)