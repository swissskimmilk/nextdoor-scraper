from selenium import webdriver
from lxml import html

from datetime import datetime, timedelta
import time
import csv
import shutil
import os

from dotenv import load_dotenv

# Variables that impact the scraper runs, change before runtime
anonymizeNames = False
numberOfPosts = 15

# Constant names for CSV files
postsFileName = "posts.csv"
postsBackupFileName = "postsBackup.csv"
repliesFileName = "replies.csv"
repliesBackupFileName = "repliesBackup.csv"

# Constant xpath strings
signinButtonPath = "//button[@id='signin_button']"
closePopupButtonPath = "//button[@class='channels-bulk-join-close-button']"
viewMorePostButtonPath = "//button[@class='truncate-view-more-link button-text button-text-no-padding']"
postNodeXpath = '//div[@class="cee-media-body"]/../..'

# Constant xpath for traversing from a postNode
# Alt paths for "For sale" posts
sponsoredHeaderPath = ".//span[@data-testid='author-children-test']/span/text()"
nextDoorHeaderPath = ".//span[@data-testid='author-children-test']/div/text()"
authorPath = ".//span[@data-testid='author-children-test']/../span[1]/a/text()"
locationPath = ".//span/*[contains(@class, 'post-byline-cursor')]/text()"
forSaleLocationPath = ".//span[@class='classified-single-item-author-byline']/text()"
titlePath = ".//*[@class='content-title-container']/span/text()"
forSaleTitlePath = ".//span[@class='classified-single-item-content-title']/text()"
categoryPath = ".//div[@class='content-scope-line']/span/*/text()"
forSaleCategoryPath = ".//div[@class='classified-single-item-scopeline']/a/text()"
datePath = ".//a[@class='post-byline-redesign']/text()"
forSaleDatePath = ".//div[@class='classified-single-item-scopeline']/span/text()"
contentPath = ".//span[@class='Linkify']/span/text()"
forSaleContentPath = ".//span[@class='Linkify']/text()"
numRepliesPath = ".//div[@data-testid='post-reply-button']/span/span[2]/text()"
numReactionsPath = ".//div[@data-testid='count-text']/text()"
commentContainerPath = ".//div[@class='js-media-comment']"
replyAuthorPath = commentContainerPath + "//a[@class='comment-detail-author-name']/text()"
replyContentPath = commentContainerPath + "//span[@class='Linkify']/span/text()"
viewMoreCommentButtonPath = ".//a[@class='truncate-view-more-link']"


def getPostNodes():
    # Get source
    htmlSource = browser.page_source
    # Encode source to readable format
    readableHtml = htmlSource.encode('utf-8')
    # Parses string readableHtml to html
    tree = html.fromstring(readableHtml)
    # Get all of the posts
    foundPostNodes = tree.xpath(postNodeXpath)
    return foundPostNodes


# Login info
emailString = os.environ.get("email")
passwordString = os.environ.get("password")

# Open Nextdoor
browser = webdriver.Chrome()
browser.get("https://nextdoor.com/login/")

# Time it takes to load the login page
time.sleep(2)

# Get input fields
username = browser.find_element_by_id("id_email")
password = browser.find_element_by_id("id_password")

# Send login info
username.send_keys(emailString)
password.send_keys(passwordString)

# Find and click the login button
browser.find_element_by_xpath(signinButtonPath).click()

# Time it takes to load homepage
time.sleep(4)

# Closes pop ups in the unlikely scenario that one appears
try:
    browser.find_element_by_xpath(closePopupButtonPath).click()
except:
    print("No popup found")
    pass

postNodes = getPostNodes()
i = 0
# Continues until it has found the specified amount of posts
while (len(postNodes) < numberOfPosts):

    # Scrolls to the bottom of the document
    print("Scrolling")
    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # Time it takes to load more content
    time.sleep(2.5)

    # Fixes the first expand button being un-clickable
    if (i == 0):
        browser.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

    # Expand all posts
    expandButtons = browser.find_elements_by_xpath(viewMorePostButtonPath)
    for j in range(0, len(expandButtons)):
        time.sleep(0.1)
        expandButtons[j].click()
        print("Expanding a post ")

    # Get all posts loaded
    postNodes = getPostNodes()
    # Remove non-user posts
    postNodes[:] = [post for post in postNodes if post.xpath(sponsoredHeaderPath) == [] and post.xpath(nextDoorHeaderPath) == []]

    i += 1
print("Posts: " + str(len(postNodes)))
# Get posts
postNodes = getPostNodes()

# Remove non-user posts
postNodes[:] = [post for post in postNodes if post.xpath(sponsoredHeaderPath) == [] and post.xpath(nextDoorHeaderPath) == []]

# Get all attributes
posts = [[''] * 10] * len(postNodes)
count = 0
for post in postNodes:
    # For standard posts
    if (post.xpath(titlePath) != []):
        posts[count] = [post.xpath(authorPath),
                        post.xpath(locationPath),
                        post.xpath(titlePath),
                        post.xpath(categoryPath),
                        post.xpath(datePath),
                        post.xpath(contentPath),
                        post.xpath(numRepliesPath),
                        post.xpath(numReactionsPath)]
    # For "For sale" posts which use different element paths and have no replies/reactions
    else:
        posts[count] = [post.xpath(authorPath),
                        post.xpath(forSaleLocationPath),
                        post.xpath(forSaleTitlePath),
                        post.xpath(forSaleCategoryPath),
                        post.xpath(forSaleDatePath),
                        post.xpath(forSaleContentPath)]
    count = count + 1

# Create a backup for posts
shutil.copyfile(postsFileName, postsBackupFileName)

# Get lines already in postsFileName
with open(postsFileName, "r") as postsFileReadOnly:
    existingLines = [line for line in csv.reader(postsFileReadOnly)]
numLines = len(existingLines)

# Add header if file is empty
with open(postsFileName, "a") as postsFileWriteOnly:
    if (os.path.getsize(postsFileName) == 0):
        postsWriter = csv.writer(postsFileWriteOnly, lineterminator='\n', quoting=csv.QUOTE_ALL)
        postsWriter.writerow(["ID", "Author", "Location", "Title", "Category", "Date", "Content", "Replies", "Reactions"])
        numLines += 1

# Create a backup for replies
shutil.copyfile(repliesFileName, repliesBackupFileName)

# Create CSV Writer for replies and a backup
repliesFile = open(repliesFileName, "w")
repliesWriter = csv.writer(repliesFile, lineterminator='\n', quoting=csv.QUOTE_ALL)

# Output to csv files
for post in posts:

    # Create ID number
    if (numLines > 1):
        with open(postsFileName, "r") as postsFileReadOnly:
            lastLine = postsFileReadOnly.readlines()[-1]
            substring = lastLine[1:]
            endIndex = substring.find("\"")
            lastID = lastLine[1:endIndex + 1]
        id = int(lastID) + 1
    else:
        id = 0
    print("Generated ID: " + str(id))

    # Get author of post
    author = post[0][0].encode('ascii', 'ignore').decode('utf8')
    if anonymizeNames:
        author = hash(str(author))
    print("Post author: " + str(author))

    # Get location of post
    try:
        location = post[1][0].encode('utf8').decode('utf8')
    except IndexError:
        location = ""
    print("Post location: " + str(location))

    # Get title of post
    title = post[2][0].encode('ascii', 'ignore').decode('utf8')
    print("Post title: " + str(title))

    # Get category of post
    category = post[3][0].encode('utf8').decode('utf8')
    print("Post category: " + str(category))

    # Get the raw date
    rawDate = post[4][0].encode('ascii', 'ignore').decode('utf8')

    # Process the raw date into a uniform format
    splitDate = rawDate.split()
    if (len(splitDate) > 2 and splitDate[2] == "ago"):
        if (splitDate[1] == "min"):
            postingTime = datetime.today() - timedelta(minutes=int(splitDate[0]))
        elif (splitDate[1] == "hr"):
            postingTime = datetime.today() - timedelta(hours=int(splitDate[0]))
        elif (splitDate[1] == "days" or splitDate[1] == "day"):
            postingTime = datetime.today() - timedelta(days=int(splitDate[0]))
        else:
            print("*ERROR: COULD NOT SUBTRACT TIME*")
        processedDate = postingTime.date()
    elif (rawDate == "Just now"):
        processedDate = datetime.today().date()
    elif (len(splitDate) == 2):
        # Zero pads the day
        splitDate[0] = splitDate[0].zfill(2)

        # %d is zero padded day, %b is shortened month, %Y is full length year. Ex: "01 May 2021"
        processedDate = datetime.strptime(splitDate[0] + " " + splitDate[1] + " " + str(datetime.today().year),
                                          "%d %b %Y").date()
    elif (len(splitDate) == 3):
        # Zero pads the day
        splitDate[0] = splitDate[0].zfill(2)

        # %d is zero padded day, %b is shortened month, %y is zero padded shortened year. Ex: "01 May 21"
        processedDate = datetime.strptime(splitDate[0] + " " + splitDate[1] + " " + splitDate[2], "%d %b %y").date()
    else:
        processedDate = ""
        print("*ERROR: DATE FORMAT NOT ADDED*")

    print("Raw date: " + str(rawDate))
    print("Processed date: " + str(processedDate))

    # Get post content
    content = post[5][0].encode('ascii', 'ignore').decode('utf8')
    content = content.replace("\n", " ")
    print("\nPost Content: " + str(content) + "\n")

    if ("For Sale" not in category):

        # Get number of replies to the post
        try:
            numReplies = post[6][0].encode('utf8').decode('utf8')
        except IndexError:
            numReplies = "0"
        print(str(numReplies) + " replies")

        # Get number of reactions to the post
        try:
            numReactions = post[7][0].encode('utf8').decode('utf8')
        except IndexError:
            numReactions = "0"
        print(str(numReactions) + " reactions")

        # Check for duplicates
        if ([author, location, title, category, str(processedDate), content] not in [existingLines[i][1:7] for i in range(0, len(existingLines))]):
            # Add entry
            with open(postsFileName, "a") as postsFileWriteOnly:
                postsWriter = csv.writer(postsFileWriteOnly, lineterminator='\n', quoting=csv.QUOTE_ALL)
                postsWriter.writerow([id, author, location, title, category, processedDate, content, numReplies, numReactions])
            numLines += 1
        else:
            print("Duplicate")
    else:
        # Check for duplicates
        if ([author, location, title, category, str(processedDate), content] not in [existingLines[i][1:7] for i in range(0, len(existingLines))]):
            # Add entry
            with open(postsFileName, "a") as postsFileWriteOnly:
                postsWriter = csv.writer(postsFileWriteOnly, lineterminator='\n', quoting=csv.QUOTE_ALL)
                postsWriter.writerow([id, author, location, title, category, processedDate, content])
            numLines += 1
        else:
            print("Duplicate")

    print("-------------------------------------")

print("Number of posts: " + str(len(posts)))
postsFileWriteOnly.close()
repliesFile.close()
browser.quit()