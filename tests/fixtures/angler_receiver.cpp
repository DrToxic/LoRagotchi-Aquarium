// Actual DX frozen COMMIT -> actual RX receiver -> companion fragments.
// Only flash/radio are mocked; no real radio or owner identity is used.
#include "LoRaFishCommit.h"
#include "LoRagotchiRX.h"
#include <assert.h>
struct Backend:lrx::IO {
  uint32_t hash=100;
  bool save(const lrx::Journal& j) override {return lrx::valid(j);}
  bool send(const uint8_t*,const char*,uint32_t& ack,uint32_t& timeout) override {
    ack=++hash;timeout=10000;return true;
  }
};
int main(int argc,char** argv) {
  if(argc>1 && !strcmp(argv[1],"colours")) {
    for(unsigned i=8;i<=247;i++)printf("%u %u\n",i,(unsigned)LoRaFishColour::rgb565(i));
    return 0;
  }
  Backend backend;lrx::Receiver receiver(backend);assert(receiver.begin(nullptr,0));
  uint8_t key[32]={1},rx[32]={3},destination[32]={4};
  const unsigned species=argc>1 ? (unsigned)strtoul(argv[1],nullptr,10) : 14;
  for(unsigned stage=0;stage<4;stage++) {
    key[0]=stage+1;
    char request[90];snprintf(request,sizeof(request),"LFG1|REQ|7|8|%u|Synthetic Angler",stage);
    receiver.receive(key,request,stage*6000);
    LoRaFishCommitFrame commit;
    commit.prepare(destination,7,8,true,8,148,6,65535,2,species,true);
    const char* payload=commit.forVisit(destination,7,8);assert(payload);
    receiver.receive(key,payload,stage*6000+1);
    // Frozen retransmission must not create a second snapshot.
    receiver.receive(key,payload,stage*6000+2);
    assert(receiver.data.slots[stage].species==species);
    assert(receiver.data.slots[stage].presence==7);
    receiver.tick(stage*6000+4001);receiver.acknowledgeRadio(backend.hash);
  }
  int lead;
  while((lead=getchar())!=EOF) {
    if(lead!='<')continue;
    int lo=getchar(),hi=getchar();if(lo<0||hi<0)return 1;
    size_t length=unsigned(lo)|(unsigned(hi)<<8);if(!length||length>176)return 2;
    uint8_t request[176],response[176];if(fread(request,1,length,stdin)!=length)return 3;
    size_t size=receiver.command(request,length,response,23000,rx,1);
    if(!size)return 4;
    putchar('>');putchar(size&255);putchar(size>>8);fwrite(response,1,size,stdout);fflush(stdout);
  }
}
