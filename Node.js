export default async function handler(req, res) {
    const { uid } = req.query;

    if (!uid) {
        return res.status(400).json({ error: "UID is required" });
    }

    try {
        // Yahan aap player ka data fetch karne ka logic dalenge
        // Example Data (Aap ise apne source se replace karein):
        const playerData = {
            status: "success",
            name: "DADDY ' sHOME♡",
            uid: uid,
            region: "IND",
            likes: 11827, // Yeh current likes hain jo server se aayenge
            api_limit: "104/220"
        };

        // Sabse important: Response JSON format mein hona chahiye
        res.setHeader('Content-Type', 'application/json');
        return res.status(200).json(playerData);

    } catch (error) {
        return res.status(500).json({ error: "API Server Error" });
    }
}
