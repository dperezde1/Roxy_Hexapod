import mqtt from 'mqtt';
import type { MqttClient } from 'mqtt';

export interface IMUData {
  pitch: number;
  roll: number;
  yaw: number;
  accelX: number;
  accelY: number;
  accelZ: number;
}

type MessageCallback = (topic: string, message: Buffer) => void;

class MqttService {
  private client: MqttClient | null = null;
  private callbacks: Map<string, MessageCallback[]> = new Map();
  private isConnected = false;

  connect(url: string, options?: mqtt.IClientOptions) {
    if (this.client) {
      this.client.end();
    }

    this.client = mqtt.connect(url, options);

    this.client.on('connect', () => {
      console.log('Connected to MQTT Broker:', url);
      this.isConnected = true;
      // Re-subscribe all topics that were registered before the connection was ready
      for (const topic of this.callbacks.keys()) {
        this.client!.subscribe(topic, (err) => {
          if (err) console.error(`Re-subscription error for ${topic}`, err);
          else console.log(`Subscribed to ${topic}`);
        });
      }
    });

    this.client.on('message', (topic, message) => {
      const topicCallbacks = this.callbacks.get(topic) || [];
      topicCallbacks.forEach((cb) => cb(topic, message));
    });

    this.client.on('error', (err) => {
      console.error('MQTT Error: ', err);
      this.isConnected = false;
      // Don't call client.end() here — let MQTT.js auto-reconnect
    });

    this.client.on('close', () => {
      console.log('Disconnected from MQTT Broker');
      this.isConnected = false;
    });
  }

  subscribe(topic: string, callback: MessageCallback) {
    if (!this.callbacks.has(topic)) {
      this.callbacks.set(topic, []);
    }
    this.callbacks.get(topic)?.push(callback);

    if (this.client && this.isConnected) {
      this.client.subscribe(topic, (err) => {
        if (err) console.error(`Subscription error for topic ${topic}`, err);
      });
    }
  }

  unsubscribe(topic: string, callback: MessageCallback) {
    const topicCallbacks = this.callbacks.get(topic);
    if (topicCallbacks) {
      this.callbacks.set(
        topic,
        topicCallbacks.filter((cb) => cb !== callback)
      );
      if (this.callbacks.get(topic)?.length === 0) {
        this.client?.unsubscribe(topic);
      }
    }
  }

  publish(topic: string, message: string | Buffer) {
    if (this.client && this.isConnected) {
      this.client.publish(topic, message);
    } else {
      console.warn('Cannot publish, MQTT client not connected');
    }
  }

  disconnect() {
    this.client?.end();
    this.isConnected = false;
  }

  getStatus() {
    return this.isConnected;
  }
}

export const mqttService = new MqttService();
