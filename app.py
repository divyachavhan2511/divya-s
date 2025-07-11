import streamlit as st
import re
import emoji
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from googleapiclient.discovery import build 
import smtplib
from PIL import Image
# Install dependencies
nltk.download('vader_lexicon')

# Function to fetch comments from YouTube
def fetch_comments(video_id, uploader_channel_id, youtube):
    comments = []
    nextPageToken = None
    while len(comments) < 600:
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=100,  # You can fetch up to 100 comments per request
            pageToken=nextPageToken
        )
        response = request.execute()
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            # Check if the comment is not from the video uploader
            if comment['authorChannelId']['value'] != uploader_channel_id:
                comments.append(comment['textDisplay'])
        nextPageToken = response.get('nextPageToken')

        if not nextPageToken:
            break

    return comments

# Function to analyze sentiment
def sentiment_scores(comment, polarity):
    # Creating a SentimentIntensityAnalyzer object
    sentiment_object = SentimentIntensityAnalyzer()

    sentiment_dict = sentiment_object.polarity_scores(comment)
    polarity.append(sentiment_dict['compound'])

    return polarity

# Function to process comments and analyze sentiment
def process_comments(video_url):
    API_KEY = 'AIzaSyBdYjf1PYnkeJhFSQJOCY_AKkIV4Xp9tKM'
    youtube = build('youtube', 'v3', developerKey=API_KEY)

    video_id_match = re.search(
        r'(?:youtu\.be\/|youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=))([^"&?\/\s]{11})',
        video_url)
    if video_id_match:
        video_id = video_id_match.group(1)

        video_response = youtube.videos().list(
            part='snippet',
            id=video_id
        ).execute()

        if 'items' in video_response and video_response['items']:
            video_snippet = video_response['items'][0]['snippet']
            uploader_channel_id = video_snippet['channelId']

            comments = fetch_comments(video_id, uploader_channel_id, youtube)

            # Process comments
            relevant_comments = []
            hyperlink_pattern = re.compile(
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            threshold_ratio = 0.65

            for comment_text in comments:
                comment_text = comment_text.lower().strip()

                emojis = emoji.emoji_count(comment_text)

                text_characters = len(re.sub(r'\s', '', comment_text))

                if (any(char.isalnum() for char in comment_text)) and not hyperlink_pattern.search(
                        comment_text):
                    if emojis == 0 or (text_characters / (text_characters + emojis)) > threshold_ratio:
                        relevant_comments.append(comment_text)

            # Analyze sentiment
            polarity = []
            positive_comments = []
            negative_comments = []
            neutral_comments = []

            for comment in relevant_comments:
                polarity = sentiment_scores(comment, polarity)

                if polarity[-1] > 0.05:
                    positive_comments.append(comment)
                elif polarity[-1] < -0.05:
                    negative_comments.append(comment)
                else:
                    neutral_comments.append(comment)

            avg_polarity = sum(polarity) / len(polarity)

            # Calculate percentages
            total_comments = len(positive_comments) + len(negative_comments) + len(neutral_comments)
            positive_percent = (len(positive_comments) / total_comments) * 100
            negative_percent = (len(negative_comments) / total_comments) * 100
            neutral_percent = (len(neutral_comments) / total_comments) * 100

            return positive_comments, negative_comments, neutral_comments, avg_polarity, positive_percent, negative_percent, neutral_percent
        else:
            return None
    else:
        return None


def send_email(sender_email, receiver_email, password, message_body):
    # Create message container
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "Streamlit Email"

    # Add body to email
    body = message_body
    message.attach(MIMEText(body, "plain"))

    # Establish a connection with the SMTP server
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()  # Secure the connection
        server.login(sender_email, password)
        text = message.as_string()
        server.sendmail(sender_email, receiver_email, text)

        st.success("Email sent successfully!")


# Add a menu for navigation
menu = ['Home', 'About', 'Contact']
choice = st.sidebar.selectbox('Menu', menu)

if choice == 'Home':
    st.title('Welcome to YouTube Comment Sentiment Analysis')
    st.subheader('Enter a YouTube Video URL to analyze comments:')
    video_url = st.text_input('Video URL:')
    if st.button('Analyze'):
        if video_url:
            positive_comments, negative_comments, neutral_comments, avg_polarity, positive_percent, negative_percent, neutral_percent = process_comments(video_url)

            if positive_comments is not None:
                st.write(f'Average Polarity: {avg_polarity}')

                # Display positive, negative, and neutral comments with percentages
                st.write(f'Positive Comments: {len(positive_comments)} ({positive_percent:.2f}%)')
                st.write(f'Negative Comments: {len(negative_comments)} ({negative_percent:.2f}%)')
                st.write(f'Neutral Comments: {len(neutral_comments)} ({neutral_percent:.2f}%)')

                # Display positive comments in a table
                st.markdown('<h2 style="color: green;">Positive Comments</h2>', unsafe_allow_html=True)
                st.table(positive_comments)

                # Display negative comments in a table
                st.markdown('<h2 style="color: red;">Negative Comments</h2>', unsafe_allow_html=True)
                st.table(negative_comments)

                # Display neutral comments in a table
                st.markdown('<h2 style="color: grey;">Neutral Comments</h2>', unsafe_allow_html=True)
                st.table(neutral_comments)

                # Plotting sentiment distribution
                import matplotlib.pyplot as plt

                labels = ['Positive', 'Negative', 'Neutral']
                comment_counts = [len(positive_comments), len(negative_comments), len(neutral_comments)]

                fig, ax = plt.subplots()
                bars = ax.bar(labels, comment_counts, color=['green', 'red', 'yellow'])
                ax.set_xlabel('Sentiment')
                ax.set_ylabel('Comment Count')
                ax.set_title('Sentiment Analysis of Comments')

                # Add numbers inside bars
                for bar, count in zip(bars, comment_counts):
                    yval = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width() / 2, yval, count, va='bottom', ha='center')

                st.pyplot(fig)


            else:
                st.write('No comments found or error processing comments.')
        else:
            st.write('Please enter a valid YouTube Video URL.')

elif choice == 'About':
    st.title('About us')
    st.header('Welcome to YouTube Comment Sentiment Analysis')
    st.write('We are a team passionate about leveraging the power of natural language processing and data analytics to understand the sentiments expressed in YouTube comments. Our goal is to provide valuable insights to content creators, marketers, and researchers by analyzing the positivity, negativity, and neutrality of comments on YouTube videos. With a combination of NLTK sentiment analysis capabilities and the YouTube Data API for fetching comments, we aim to deliver an intuitive and insightful platform for analyzing and visualizing comment sentiments. Join us on this journey as we dive deep into the sentiments behind every comment, empowering you to make data-driven decisions and understand audience perceptions better.')
    st.write('-By Divya Chavhan and Rudra Khadela')

elif choice == 'Contact':
    st.header('Contact Us')
    
    # Display profile photos
    col1, col2 = st.columns(2)
    with col1:
        divya_photo = Image.open('divya_photo.jpg').resize((200, 200))  # Set equal height and width (e.g., 100x100)
        st.image(divya_photo, caption='Divya Chavhan')
    with col2:
        rudra_photo = Image.open('rudra_photo.jpg').resize((200, 200))  # Set equal height and width (e.g., 100x100)
        st.image(rudra_photo, caption='Rudra Khadela')

    # Display LinkedIn profiles
    st.write('Connect with us on LinkedIn:')
    st.markdown('[Divya Chavhan](https://www.linkedin.com/in/divya-chavhan-18027a253?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app)')
    st.markdown('[Rudra Khadela](https://www.linkedin.com/in/rudra-khadela-49427a253?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app)')
    
    st.subheader('Reach out to us:')
    
# Streamlit UI
st.markdown("""
    <style>
        .big-title {
            animation: scale-in-center 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
        }

        @keyframes scale-in-center {
            0% {
                transform: scale(0);
                opacity: 0;
            }
            100% {
                transform: scale(1);
                opacity: 1;
            }
        }

        h1, h2, h3, h4, h5, h6 {
            animation: slide-in-left 0.5s ease-out both;
        }

        @keyframes slide-in-left {
            0% {
                transform: translateX(-100%);
                opacity: 0;
            }
            100% {
                transform: translateX(0);
                opacity: 1;
            }
        }
    </style>
""", unsafe_allow_html=True)