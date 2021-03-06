import logging
import operations
import os
import sys

from sets import Set

# import common package in parent directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'config'))

import mongodb_client
from cloudAMQP_client import CloudAMQPClient
from config import Config as cfg

cf = cfg().load_config_file()['operations']
cf2 = cfg().load_config_file()['logging']['loggers']['keys']
print cf2[1]
app_log = logging.getLogger(cf2[1] + __name__)
# TODO: use your own queue.
LOG_CLICKS_TASK_QUEUE_URL = cf['LOG_CLICKS_TASK_QUEUE_URL']
LOG_CLICKS_TASK_QUEUE_NAME = cf['LOG_CLICKS_TASK_QUEUE_NAME']

CLICK_LOGS_TABLE_NAME = cf['CLICK_LOGS_TABLE_NAME']

cloudAMQP_client = CloudAMQPClient(LOG_CLICKS_TASK_QUEUE_URL, LOG_CLICKS_TASK_QUEUE_NAME)


# Start Redis, MongoDB and recommandation_service before running following tests.

def test_getNewsSummariesForUser_basic():
    news = operations.getNewsSummariesForUser('test', 1)
    print news
    assert len(news) > 0
    app_log.info('test_getNewsSummariesForUser_basic passed!')


def test_getNewsSummariesForUser_pagination():
    news_page_1 = operations.getNewsSummariesForUser('test', 1)
    news_page_2 = operations.getNewsSummariesForUser('test', 2)

    assert len(news_page_1) > 0
    assert len(news_page_2) > 0

    # Assert that there is no dupe news in two pages.
    digests_page_1_set = Set([news['digest'] for news in news_page_1])
    digests_page_2_set = Set([news['digest'] for news in news_page_2])
    assert len(digests_page_1_set.intersection(digests_page_2_set)) == 0

    app_log.info('test_getNewsSummariesForUser_pagination passed!')


def test_logNewsClickForUser_basic():
    db = mongodb_client.get_db()
    #db[CLICK_LOGS_TABLE_NAME].delete_many({"userId": "test"})

    operations.logNewsClickForUser('test', 'test_news', False, True)

    # Verify click logs written into MongoDB
    # Get most recent record in MongoDB.
    record = list(db[CLICK_LOGS_TABLE_NAME].find().sort([('timestamp', -1)]).limit(1))[0]

    assert record is not None
    assert record['userId'] == 'test'
    assert record['newsId'] == 'test_news'
    assert record['timestamp'] is not None

    db[CLICK_LOGS_TABLE_NAME].delete_many({"userId": "test"})

    # Verify the message has been sent to queue. Delay may occur and please re-run after a while if this test failed
    msg = cloudAMQP_client.getMessage()
    assert msg is not None
    assert msg['userId'] == 'test'
    assert msg['newsId'] == 'test_news'
    assert msg['timestamp'] is not None

    app_log.info('test_logNewsClicksForUser_basic passed!')


if __name__ == "__main__":
    test_getNewsSummariesForUser_basic()
    test_getNewsSummariesForUser_pagination()
    test_logNewsClickForUser_basic()
