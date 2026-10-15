import * as fflate from 'fflate';

self.onmessage = (e) => {
    const buffer = e.data;
    try {
        const unzipped = fflate.unzipSync(new Uint8Array(buffer));
        let extractedText = "";
        const decoder = new TextDecoder();
        
        for (const filename in unzipped) {
            // Skip directories and common binary files
            if (filename.match(/\.(png|jpg|jpeg|gif|ico|pdf|exe|dll|zip|tar|gz|mp4|webm|woff|woff2|ttf|eot)$/i)) continue;
            if (filename.includes("node_modules/") || filename.includes(".git/")) continue;
            
            const fileData = unzipped[filename];
            if (fileData.length === 0) continue; // directory or empty file
            
            const text = decoder.decode(fileData);
            extractedText += `\n--- File: ${filename} ---\n` + text;
            
            // Safety limit to avoid huge memory spike when sending back to main thread
            if (extractedText.length > 500000) {
                extractedText += "\n... [TRUNCATED - ZIP TOO LARGE] ...\n";
                break;
            }
        }
        
        if (!extractedText.trim()) {
            self.postMessage({ success: true, text: "No text or log files were found in this zip!" });
        } else {
            self.postMessage({ success: true, text: extractedText.trim() });
        }
    } catch (err) {
        self.postMessage({ success: false, error: err.message });
    }
};
