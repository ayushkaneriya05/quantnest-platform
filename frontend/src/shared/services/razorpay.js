let checkoutScript;
export function loadRazorpaySdk() {
  if (window.Razorpay) return Promise.resolve(window.Razorpay);
  if (!checkoutScript)
    checkoutScript = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      const timer = setTimeout(() => {
        script.remove();
        checkoutScript = null;
        reject(new Error("Checkout could not load. Please retry."));
      }, 12000);
      script.onload = () => {
        clearTimeout(timer);
        resolve(window.Razorpay);
      };
      script.onerror = () => {
        clearTimeout(timer);
        script.remove();
        checkoutScript = null;
        reject(new Error("Checkout is unavailable. Please retry."));
      };
      document.head.append(script);
    });
  return checkoutScript;
}
