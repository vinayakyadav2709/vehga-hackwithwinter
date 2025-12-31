import { TensorflowModel, loadTensorflowModel } from 'react-native-fast-tflite';
import * as ImageManipulator from 'expo-image-manipulator';
import * as FileSystem from 'expo-file-system';
import { useAssets } from 'expo-asset';
import { useState, useEffect } from 'react';
import jpeg from 'jpeg-js';
import { Buffer } from 'buffer';

// Polyfill Buffer
global.Buffer = global.Buffer || Buffer;

const ModelPath = require('../../assets/models/yolov8n.tflite');

// COCO Vehicle Classes
const VEHICLE_CLASSES: { [key: number]: string } = {
    2: 'car',
    3: 'motorcycle',
    5: 'bus',
    7: 'truck'
};

export function useYoloModel() {
    const [assets] = useAssets([ModelPath]);
    const [model, setModel] = useState<TensorflowModel | null>(null);
    const [modelState, setModelState] = useState<'loading' | 'loaded' | 'error'>('loading');

    useEffect(() => {
        async function load() {
            if (!assets || !assets[0]) return;

            try {
                const modelUri = assets[0].localUri || assets[0].uri;
                const m = await loadTensorflowModel({ url: modelUri });

                // Warmup
                const dummy = new Uint8Array(320 * 320 * 3);
                m.runSync([dummy]);

                setModel(m);
                setModelState('loaded');
            } catch (e) {
                console.error('Model load error:', e);
                setModelState('error');
            }
        }
        load();
    }, [assets]);

    return { model, modelState };
}

export async function runYoloInference(
    model: TensorflowModel,
    imageUri: string,
    threshold: number = 0.30
): Promise<{ count: number; detections: Array<{ label: string; score: number }> }> {
    try {
        // 1. Resize to 320x320
        const manipResult = await ImageManipulator.manipulateAsync(
            imageUri,
            [{ resize: { width: 320, height: 320 } }],
            { compress: 1, format: ImageManipulator.SaveFormat.JPEG }
        );

        // 2. Read as Base64
        const file = new FileSystem.File(manipResult.uri);
        const base64 = await file.base64();

        // 3. Decode JPEG to RGB
        const buffer = Buffer.from(base64, 'base64');
        const rawData = jpeg.decode(buffer, { useTArray: true });

        // 4. Convert RGBA -> RGB
        const rgba = rawData.data;
        const rgb = new Uint8Array(320 * 320 * 3);
        let p = 0;
        for (let i = 0; i < rgba.length; i += 4) {
            rgb[p++] = rgba[i];
            rgb[p++] = rgba[i + 1];
            rgb[p++] = rgba[i + 2];
        }

        // 5. Run Inference
        const output = model.runSync([rgb]);
        const classes = output[1];
        const scores = output[2];

        // 6. Parse Detections (Vehicles Only)
        const detections: Array<{ label: string; score: number }> = [];
        let vehicleCount = 0;

        for (let i = 0; i < 25; i++) {
            const score = Number(scores[i]);
            if (score > threshold) {
                const classId = Number(classes[i]);
                if (VEHICLE_CLASSES[classId]) {
                    vehicleCount++;
                    detections.push({
                        label: VEHICLE_CLASSES[classId],
                        score
                    });
                }
            }
        }

        return { count: vehicleCount, detections };
    } catch (error) {
        console.error('Inference error:', error);
        throw error;
    }
}
