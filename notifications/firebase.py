# notifications/firebase.py
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if not firebase_admin._apps:
        try:
            # Path to your Firebase service account key JSON file
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
            raise


def send_push_notification(fcm_token, title, body, data=None):
    """
    Send push notification to a single device
    
    Args:
        fcm_token (str): Firebase Cloud Messaging token
        title (str): Notification title
        body (str): Notification body
        data (dict): Additional data to send with notification
    
    Returns:
        str: Message ID if successful, None otherwise
    """
    try:
        # Ensure Firebase is initialized
        initialize_firebase()
        
        # Create notification message
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
        )
        
        # Send message
        response = messaging.send(message)
        logger.info(f"Successfully sent message: {response}")
        return response
    
    except Exception as e:
        logger.error(f"Error sending push notification: {str(e)}")
        return None


def send_multicast_notification(fcm_tokens, title, body, data=None):
    """
    Send push notification to multiple devices
    
    Args:
        fcm_tokens (list): List of FCM tokens
        title (str): Notification title
        body (str): Notification body
        data (dict): Additional data to send with notification
    
    Returns:
        tuple: (Response object containing success/failure counts, list of invalid tokens)
    """
    invalid_tokens = []
    
    try:
        # Ensure Firebase is initialized
        initialize_firebase()
        
        # Convert data values to strings (FCM requires string values)
        string_data = {}
        if data:
            for key, value in data.items():
                string_data[key] = str(value) if not isinstance(value, str) else value
        
        # Send to each token individually using send_each (new API)
        # or send_all if available
        messages = [
            messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=string_data,
                token=token,
            )
            for token in fcm_tokens
        ]
        
        # Use send_each for newer firebase-admin versions
        if hasattr(messaging, 'send_each'):
            response = messaging.send_each(messages)
            # Check for invalid tokens
            for idx, send_response in enumerate(response.responses):
                if not send_response.success:
                    error = send_response.exception
                    # Check if token is invalid/expired
                    if error and hasattr(error, 'code'):
                        error_code = str(error.code) if hasattr(error.code, '__str__') else error.code
                        if any(code in str(error_code).lower() for code in ['invalid', 'not-registered', 'unregistered']):
                            invalid_tokens.append(fcm_tokens[idx])
                            logger.warning(f"Invalid token detected: {fcm_tokens[idx][:20]}...")
        elif hasattr(messaging, 'send_all'):
            response = messaging.send_all(messages)
            # Check for invalid tokens
            for idx, send_response in enumerate(response.responses):
                if not send_response.success:
                    error = send_response.exception
                    if error and hasattr(error, 'code'):
                        error_code = str(error.code) if hasattr(error.code, '__str__') else error.code
                        if any(code in str(error_code).lower() for code in ['invalid', 'not-registered', 'unregistered']):
                            invalid_tokens.append(fcm_tokens[idx])
        else:
            # Fallback: send individually
            success_count = 0
            failure_count = 0
            for idx, message in enumerate(messages):
                try:
                    messaging.send(message)
                    success_count += 1
                except Exception as e:
                    failure_count += 1
                    # Check if token is invalid
                    if hasattr(e, 'code'):
                        error_code = str(e.code) if hasattr(e.code, '__str__') else e.code
                        if any(code in str(error_code).lower() for code in ['invalid', 'not-registered', 'unregistered']):
                            invalid_tokens.append(fcm_tokens[idx])
            
            # Create a simple response object
            class SimpleResponse:
                def __init__(self, success, failure):
                    self.success_count = success
                    self.failure_count = failure
            
            return SimpleResponse(success_count, failure_count), invalid_tokens
        
        logger.info(f"Successfully sent {response.success_count} messages")
        if response.failure_count > 0:
            logger.warning(f"Failed to send {response.failure_count} messages")
        if invalid_tokens:
            logger.info(f"Found {len(invalid_tokens)} invalid tokens to be cleaned up")
        
        return response, invalid_tokens
    
    except Exception as e:
        logger.error(f"Error sending multicast notification: {str(e)}")
        return None, invalid_tokens


def send_topic_notification(topic, title, body, data=None):
    """
    Send notification to a topic
    
    Args:
        topic (str): Topic name
        title (str): Notification title
        body (str): Notification body
        data (dict): Additional data to send with notification
    
    Returns:
        str: Message ID if successful, None otherwise
    """
    try:
        # Ensure Firebase is initialized
        initialize_firebase()
        
        # Create topic message
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            topic=topic,
        )
        
        # Send message
        response = messaging.send(message)
        logger.info(f"Successfully sent message to topic {topic}: {response}")
        return response
    
    except Exception as e:
        logger.error(f"Error sending topic notification: {str(e)}")
        return None


def subscribe_to_topic(fcm_tokens, topic):
    """
    Subscribe devices to a topic
    
    Args:
        fcm_tokens (list): List of FCM tokens
        topic (str): Topic name
    
    Returns:
        TopicManagementResponse: Response object
    """
    try:
        initialize_firebase()
        response = messaging.subscribe_to_topic(fcm_tokens, topic)
        logger.info(f"Successfully subscribed {response.success_count} tokens to topic {topic}")
        return response
    except Exception as e:
        logger.error(f"Error subscribing to topic: {str(e)}")
        return None


def unsubscribe_from_topic(fcm_tokens, topic):
    """
    Unsubscribe devices from a topic
    
    Args:
        fcm_tokens (list): List of FCM tokens
        topic (str): Topic name
    
    Returns:
        TopicManagementResponse: Response object
    """
    try:
        initialize_firebase()
        response = messaging.unsubscribe_from_topic(fcm_tokens, topic)
        logger.info(f"Successfully unsubscribed {response.success_count} tokens from topic {topic}")
        return response
    except Exception as e:
        logger.error(f"Error unsubscribing from topic: {str(e)}")
        return None
