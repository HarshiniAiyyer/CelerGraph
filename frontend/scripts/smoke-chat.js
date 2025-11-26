import http from 'http';

const message = process.argv[2] || 'hello from smoke test';

function send(url) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify({ message });
    const req = http.request(new URL(url), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      }
    }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let data;
        try { data = JSON.parse(text); } catch { data = { raw: text }; }
        resolve({ status: res.statusCode, data });
      });
    });
    req.on('error', (err) => reject(err));
    req.write(payload);
    req.end();
  });
}

async function main() {
  let result;
  let used;
  try {
    used = 'http://127.0.0.1:5173/api/chat';
    result = await send(used);
  } catch {
    used = 'http://127.0.0.1:8000/api/chat';
    result = await send(used);
  }
  console.log(JSON.stringify({ url: used, status: result.status, data: result.data }, null, 2));
  if (result.status < 200 || result.status >= 300) process.exitCode = 1;
}

main();
