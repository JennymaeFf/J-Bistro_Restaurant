/*  */import Image from 'next/image';

const menuItems = [
  { name: 'P60 Cheeseburger', img: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80', alt: 'Cheeseburger' },
  { name: 'P50 Cheese Sandwich', img: 'https://images.unsplash.com/photo-1559054663-e8d23213f55c?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80', alt: 'Cheese Sandwich' },
  { name: 'P60 Chicken Burger', img: 'https://images.unsplash.com/photo-1607013251420-7c76c8cd0d8d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80', alt: 'Chicken Burger' },
  { name: 'P99 Spicy Chicken', img: 'https://images.unsplash.com/photo-1626082927389-0a1e2c3d5c0a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80', alt: 'Spicy Chicken' },
  { name: 'P99 Beef Steak', img: 'https://images.unsplash.com/photo-1544025162-d766942659f8?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80', alt: 'Beef Steak' },
  { name: 'P99 Salmon Fillet', img: 'https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80', alt: 'Salmon Fillet' },
];

export default function Dashboard() {
  return (
    <div className="relative min-h-screen font-sans" style={{ color: '#4a3c31' }}>
      <Image src="/bg.png" alt="Background" fill className="object-cover" priority sizes="100vw" />
      <div className="fixed inset-0 z-[1]" style={{ background: 'rgba(245,224,194,0.75)' }} />

      <div className="relative z-10 flex flex-col min-h-screen">

        {/* Navbar */}
        <nav className="bg-[#8d5524] text-white py-4 px-6 shadow-md flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image src="/plogo.png" alt="J'Bistro Logo" width={40} height={40} className="h-10 w-auto" />
            <span className="text-2xl font-bold">J&apos;Bistro</span>
          </div>
          <div className="flex items-center gap-8">
            <a href="#" className="hover:underline">Our Menu</a>
            <a href="#" className="hover:underline">About</a>
            <a href="#" className="hover:underline">Cart</a>
            <div className="w-10 h-10 rounded-full bg-gray-300 flex items-center justify-center text-gray-700 font-bold">
              👤
            </div>
          </div>
        </nav>

        {/* Sidebar + Main */}
        <div className="flex flex-1">

          {/* Sidebar */}
          <aside className="w-64 py-8 px-6 hidden md:block" style={{ background: '#d4a373', color: 'white' }}>
            <h2 className="text-xl font-bold mb-6">Categories</h2>
            <ul className="space-y-4">
              <li><a href="#" className="block py-2 px-4 bg-[#a66c3c] rounded-lg">Main Course</a></li>
              <li><a href="#" className="block py-2 px-4 hover:bg-[#a66c3c] rounded-lg">Appetizers</a></li>
              <li><a href="#" className="block py-2 px-4 hover:bg-[#a66c3c] rounded-lg">Beverage</a></li>
            </ul>
          </aside>

          {/* Menu Grid */}
          <main className="flex-1 p-8">
            <h1 className="text-4xl font-bold mb-8 text-center md:text-left">Main Course</h1>
            <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              {menuItems.map((item) => (
                <div key={item.name} className="bg-white rounded-xl shadow-lg overflow-hidden">
                  <img src={item.img} alt={item.alt} className="w-full h-48 object-cover" />
                  <div className="p-4 text-center">
                    <h3 className="font-bold text-lg">{item.name}</h3>
                  </div>
                </div>
              ))}
            </div>
          </main>

        </div>
      </div>
    </div>
  );
}
