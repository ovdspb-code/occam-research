const oldLocation = document.getElementById(location.hash.slice(1));
const destination = oldLocation?.closest('.index-links a');
if (destination) {
  const target = new URL(destination.href);
  if (oldLocation !== destination) target.hash = oldLocation.id;
  location.replace(target);
}
