import streamlit as st
import json
from datetime import datetime
from azure.cosmos import CosmosClient
import html

# initialize_cosmos_client with toml


def initialize_cosmos_client():
    endpoint = st.secrets["cosmosdb"]["COSMOS_DB_ENDPOINT"]
    key = st.secrets["cosmosdb"]["COSMOS_DB_KEY"]
    client = CosmosClient(endpoint, key)
    database = client.get_database_client(
        st.secrets["cosmosdb"]["COSMOS_DB_DATABASE_NAME"])
    container = database.get_container_client(
        st.secrets["cosmosdb"]["COSMOS_DB_CONTAINER_NAME"])
    return container


def get_last_10_tweets(container):
    query = """
    SELECT TOP 10 *
    FROM c
    ORDER BY c.created_at DESC
    """
    return list(container.query_items(query=query, enable_cross_partition_query=True))


def get_elon_tweets(container, limit=10):
    query = f"""
    SELECT TOP {limit} *
    FROM c
    WHERE c.author.username = 'elonmusk'
    ORDER BY c.created_at DESC
    """
    return list(container.query_items(query=query, enable_cross_partition_query=True))


def get_tweet_thread(container, tweet):
    thread = [tweet]
    current_tweet = tweet
    while 'referenced_tweets' in current_tweet:
        for ref in current_tweet['referenced_tweets']:
            if ref['type'] == 'replied_to':
                query = f"SELECT * FROM c WHERE c.id = '{ref['id']}'"
                items = list(container.query_items(
                    query=query, enable_cross_partition_query=True))
                if items:
                    thread.insert(0, items[0])
                    current_tweet = items[0]
                    break
        else:
            break
    return thread


def format_date(date_string):
    tweet_date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    return tweet_date.strftime("%I:%M %p · %b %d, %Y")


def display_tweet_thread(thread):
    st.markdown("""
    <style>
    .tweet-container {
        border: 1px solid #cfd9de;
        border-radius: 16px;
        padding: 12px;
        margin-bottom: 12px;
        background-color: #ffffff;
    }
    .referenced-tweet {
        background-color: #f7f9f9;
    }
    .reply-tweet {
        margin-left: 20px;
        border-left: 2px solid #cfd9de;
    }
    .replying-to {
        color: #536471;
        font-size: 13px;
        margin-left: 20px;
        margin-bottom: 5px;
    }
    .tweet-header {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
    }
    .tweet-author-image {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .tweet-author-name {
        font-weight: bold;
        margin-bottom: 0;
    }
    .tweet-author-username {
        color: #536471;
    }
    .tweet-text {
        margin-bottom: 12px;
    }
    .tweet-date {
        color: #536471;
        font-size: 14px;
        margin-bottom: 12px;
    }
    .tweet-metrics {
        display: flex;
        justify-content: space-between;
        color: #536471;
    }
    </style>
    """, unsafe_allow_html=True)

    for i, tweet in enumerate(thread):
        css_class = "referenced-tweet" if i < len(thread) - \
            1 else "reply-tweet"
        st.markdown(
            f'<div class="tweet-container {css_class}">', unsafe_allow_html=True)
        display_tweet_content(tweet)
        st.markdown('</div>', unsafe_allow_html=True)

        if i < len(thread) - 1:
            st.markdown(f'<p class="replying-to">Replying to @{
                        tweet["author"]["username"]}</p>', unsafe_allow_html=True)


def display_tweet_content(tweet):
    # Tweet header
    st.markdown(f"""
    <div class="tweet-header">
        <img src="{tweet['author']['profile_image_url']}" class="tweet-author-image">
        <div>
            <p class="tweet-author-name">{html.escape(tweet['author']['name'])}</p>
            <p class="tweet-author-username">@{html.escape(tweet['author']['username'])}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tweet text
    st.markdown(
        f'<p class="tweet-text">{html.escape(tweet["text"])}</p>', unsafe_allow_html=True)

    # Media
    if 'media' in tweet:
        for media in tweet['media']:
            if media['type'] == 'photo':
                st.image(media['url'])
            elif media['type'] == 'video':
                st.write("Video content available (cannot be displayed directly)")
                if 'preview_image_url' in media:
                    st.image(media['preview_image_url'])

    # Tweet date
    st.markdown(
        f'<p class="tweet-date">{format_date(tweet["created_at"])}</p>', unsafe_allow_html=True)

    # Tweet metrics
    metrics_html = '<div class="tweet-metrics">'
    metrics_html += f'<span>🔁 {tweet["public_metrics"]
                               ["retweet_count"]}</span>'
    metrics_html += f'<span>💬 {tweet["public_metrics"]["reply_count"]}</span>'
    metrics_html += f'<span>❤️ {tweet["public_metrics"]["like_count"]}</span>'
    metrics_html += f'<span>🔄 {tweet["public_metrics"]["quote_count"]}</span>'
    metrics_html += f'<span>🔖 {
        tweet["public_metrics"].get("bookmark_count", "N/A")}</span>'
    metrics_html += f'<span>👁️ {tweet["public_metrics"].get(
        "impression_count", "N/A")}</span>'
    metrics_html += '</div>'
    st.markdown(metrics_html, unsafe_allow_html=True)

    # Additional Tweet Information
    with st.expander("Additional Tweet Information"):
        st.json({
            "id": tweet['id'],
            "conversation_id": tweet['conversation_id'],
            "lang": tweet['lang'],
            "possibly_sensitive": tweet.get('possibly_sensitive', 'N/A'),
            "reply_settings": tweet.get('reply_settings', 'N/A'),
            "edit_controls": tweet.get('edit_controls', 'N/A'),
            "author_info": {
                "id": tweet['author']['id'],
                "created_at": tweet['author']['created_at'],
                "description": tweet['author'].get('description', 'N/A'),
                "location": tweet['author'].get('location', 'Not specified'),
                "verified": tweet['author'].get('verified', 'N/A'),
                "verified_type": tweet['author'].get('verified_type', 'Not specified'),
                "public_metrics": tweet['author'].get('public_metrics', {})
            }
        })


def main():
    st.set_page_config(layout="wide")

    container = initialize_cosmos_client()

    # Sidebar
    st.sidebar.title("Options")
    display_option = st.sidebar.radio(
        "Choose what to display:",
        ("Last 10 Elon Tweets", "All Tweet Threads")
    )

    if display_option == "Last 10 Elon Tweets":
        st.title("Elon Musk's Last 10 Tweets")
        tweets = get_elon_tweets(container)

        for i, tweet in enumerate(tweets, 1):
            st.subheader(f"Tweet {i}")
            thread = get_tweet_thread(container, tweet)
            display_tweet_thread(thread)
            st.markdown("---")
    else:
        st.title("All Tweet Threads")
        tweets = get_last_10_tweets(container)

        for i, tweet in enumerate(tweets, 1):
            st.subheader(f"Tweet Thread {i}")
            thread = get_tweet_thread(container, tweet)
            display_tweet_thread(thread)
            st.markdown("---")


if __name__ == "__main__":
    main()
